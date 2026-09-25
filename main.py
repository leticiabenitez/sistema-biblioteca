import bcrypt
from flask import Flask, render_template, request, redirect, url_for, flash, session
import fdb
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SECRET_KEY'] = 'chave_secreta_da_turma_b'

host = "localhost"
database = r"C:\Users\Aluno\Desktop\SISTEMA-BIBLIOTECA\LIVRO.FDB"
user = "sysdba"
password = "sysdba"

con = fdb.connect(host=host, database=database, user=user, password=password)

def validar_senha(senha):
    min_caractere = False
    min_upper = False
    min_lower = False
    min_num = False
    min_caractere_esp = False

    if len(senha) >= 8:
        min_caractere = True

    for caractere in senha:
        if caractere.isalpha() and caractere == caractere.upper():
            min_upper = True
        if caractere.isalpha() and caractere == caractere.lower():
            min_lower = True
        if caractere.isdigit():
            min_num = True
        if not caractere.isalpha() and not caractere.isdigit():
            min_caractere_esp = True

    if min_caractere == True and min_upper == True and min_lower == True and min_num == True and min_caractere_esp == True:
        validacao = True
        return(validacao)
    else:
        validacao = False
        return(validacao)

@app.route("/")
def index():
    return home()

@app.route("/home")
def home():
    cursor = con.cursor()
    cursor.execute("""SELECT l.ID_LIVRO, l.TITULO, l.AUTOR, l.ANO_PUBLICACAO
    FROM LIVRO l""")
    livros = cursor.fetchall()
    cursor.close()

    return render_template("livros.html", livros=livros)

@app.route("/pagina_login")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    senha = request.form["senha"]

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT ID_USUARIO, SENHA, COALESCE(STATUS, 1) FROM USUARIO WHERE EMAIL = ?""", (email,))
        usuario = cursor.fetchone()
        if usuario[2] == 1:
            if usuario:
                id_usuario, senha_banco = usuario
                if check_password_hash(senha_banco, senha):
                    session['id_usuario'] = id_usuario
                    return redirect(url_for("home"))
                else:
                    cursor.execute("""UPDATE USUARIO SET TENTATIVAS = TENTATIVAS + 1 WHERE ID_USUARIO = ? """, (usuario[0],))
                    erros = cursor.fetchone()
                    con.commit()
                    if erros == 3:
                        flash("BLOQUEADO: 3 tentativas erradas!", "error")
                        cursor.execute("""UPDATE USUARIO SET STATUS = 0 WHERE ID_USUARIO = ?""", (usuario[0],))
                        con.commit()

                    flash("Senha incorreta!", "error")
                    return redirect(url_for('login_page'))
            else:
                flash("E-mail não cadastrado!", "error")
                return redirect(url_for("login_page"))
        else:
            flash("Usuário inativo!", "error")
            return redirect(url_for("login_page"))
    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        con.rollback()
    finally:
        cursor.close()

@app.route('/logout')
def logout():
    session.pop('id_usuario', None)
    flash('Sessão encerrada. Faça login novamente.')
    return redirect(url_for('index'))

@app.route("/novo")
def novo():
    if 'id_usuario' not in session:
        flash('É necessário realizar o login', 'error')
        return redirect(url_for('index'))

    return render_template("novo.html")


@app.route("/criar", methods=["POST"])
def criar():
    if 'id_usuario' not in session:
        flash('Faça login primeiro!', 'error')
        return redirect(url_for('login_page'))

    titulo = request.form["titulo"]
    autor = request.form["autor"]
    ano_publicacao = request.form["ano_publicacao"]

    cursor = con.cursor()
    try:
        cursor.execute("""SELECT 1 FROM LIVRO WHERE upper(TITULO) = ?""", (titulo.upper(),))
        if cursor.fetchone():
            flash("Erro: Livro já existe!", "error")
            return redirect(url_for('novo'))
        cursor.execute("""INSERT INTO LIVRO (TITULO,AUTOR,ANO_PUBLICACAO)
                       VALUES (?,?,?) RETURNING ID_LIVRO""", (titulo, autor, ano_publicacao))
        id_livro = cursor.fetchone()[0]
        con.commit()

        arquivo = request.files["imagem"]
        arquivo.save(f"uploads/capa{id_livro}.jpg")

        flash("Livro cadastrado com sucesso!", "success")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        con.rollback()
    finally:
        cursor.close()

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if 'id_usuario' not in session:
        flash('Faça login primeiro!', 'error')
        return redirect(url_for('login_page'))

    cursor = con.cursor()
    try:
        cursor.execute("""SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO FROM LIVRO
                       WHERE ID_LIVRO = ?""", (id,))
        livro = cursor.fetchone()

        if not livro:
            flash("Livro não encontrado!", "error")
            return redirect(url_for('home'))

        if request.method == "POST":
            titulo = request.form["titulo"]
            autor = request.form["autor"]
            ano_publicacao = request.form["ano_publicacao"]

            cursor.execute("""UPDATE LIVRO SET TITULO = ?, AUTOR = ?, ANO_PUBLICACAO = ?
                           WHERE ID_LIVRO = ?""", (titulo,autor,ano_publicacao, id))
            con.commit()
            flash("Livro editado com sucesso!", "success")
            return redirect(url_for('home'))
        else:
            return render_template("editar.html", livro=livro)

    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        con.rollback()
    finally:
        cursor.close()


@app.route("/confirmar_exclusao/<int:id>", methods=["GET"])
def confirmar_exclusao(id):
    if 'id_usuario' not in session:
        flash('Faça login primeiro!', 'error')
        return redirect(url_for('login_page'))

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO
                            FROM LIVRO WHERE ID_LIVRO = ?""", (id,))
        livro = cursor.fetchone()

        if not livro:
            flash("Livro não encontrado!", "error")
            return redirect(url_for('home'))

        return render_template("confirmar_delete.html", livro=livro)

    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        con.rollback()
        return redirect(url_for('home'))

    finally:
        cursor.close()

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    if 'id_usuario' not in session:
        flash('Faça login primeiro!', 'error')
        return redirect(url_for('login_page'))

    cursor = con.cursor()

    try:
        cursor.execute("""DELETE FROM LIVRO
                              WHERE ID_LIVRO = ?""", (id,))
        con.commit()
        flash("Livro excluído com sucesso!", "success")
        return redirect(url_for('home'))

    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        con.rollback()
        return redirect(url_for('home'))

    finally:
        cursor.close()

@app.route("/novo_usuario")
def novo_usuario():
    return render_template("cadastrar_usuario.html")

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form["nome"]
    email = request.form["email"]
    senha = request.form["senha"]

    cursor = con.cursor()
    try:
        cursor.execute("""SELECT 1 FROM USUARIO WHERE upper(EMAIL) = ?""", (email.upper(), ))
        if cursor.fetchone():
            flash("E-mail já está sendo usado por outro usuário", "error")
            return redirect(url_for('novo_usuario'))
        if validar_senha(senha) == True:
            senha_crip = generate_password_hash (senha)

            cursor.execute("""INSERT INTO USUARIO (NOME, EMAIL, SENHA, STATUS) 
                              VALUES (?,?,?,1)""", (nome, email, senha_crip))
            con.commit()
            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for('login_page'))
        else:
            flash("Senha não atende aos requisitos!", "error")
            return redirect(url_for('novo_usuario'))
    except Exception as e:
        flash(f"Ocorreu um erro: {e}", "error")
        return redirect(url_for('novo_usuario'))
    finally:
        cursor.close()


if __name__ == "__main__":
    app.run(debug=True)