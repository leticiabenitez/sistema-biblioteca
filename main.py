from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import fdb
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF

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
        cursor.execute("""SELECT ID_USUARIO, SENHA, COALESCE(STATUS, 1), COALESCE(TENTATIVAS, 0) FROM USUARIO WHERE EMAIL = ?""", (email,))
        usuario = cursor.fetchone()

        if usuario:
            if usuario[2] == 1:
                id_usuario, senha_banco, status, tentativas = usuario
                if check_password_hash(senha_banco, senha):
                    session['id_usuario'] = id_usuario
                    return redirect(url_for("home"))
                else:
                    cursor.execute("""UPDATE USUARIO SET TENTATIVAS = COALESCE(TENTATIVAS, 0) + 1 WHERE ID_USUARIO = ? """, (usuario[0],))
                    cursor.execute("""SELECT TENTATIVAS FROM USUARIO WHERE ID_USUARIO = ?""", (usuario[0],))
                    erros = cursor.fetchone()[0]
                    con.commit()
                    if erros == 3:
                        flash("BLOQUEADO: 3 tentativas erradas!", "error")
                        cursor.execute("""UPDATE USUARIO SET STATUS = 0 WHERE ID_USUARIO = ?""", (usuario[0],))
                        con.commit()
                        return redirect(url_for('login_page'))

                    flash("Senha incorreta!", "error")
                    return redirect(url_for('login_page'))
            else:
                flash("Usuário inativo!", "error")
                return redirect(url_for("login_page"))
        else:
                flash("E-mail não cadastrado!", "error")
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


@app.route('/livros/relatorio', methods=['GET'])
def relatorio():

    from datetime import datetime

    cursor = con.cursor()

    cursor.execute("""
        SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO
        FROM LIVRO
        ORDER BY ID_LIVRO
    """)

    livros = cursor.fetchall()
    cursor.close()

    # --------------------------------------------------
    # CONFIGURAÇÃO DO PDF
    # --------------------------------------------------

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Cores
    azul_marinho = (15, 39, 71)
    azul_claro = (225, 233, 242)
    cinza = (100, 110, 120)
    branco = (255, 255, 255)
    preto = (35, 40, 45)

    # --------------------------------------------------
    # CABEÇALHO
    # --------------------------------------------------

    # Faixa azul-marinho
    pdf.set_fill_color(*azul_marinho)
    pdf.rect(0, 0, 210, 43, "F")

    # Nome da biblioteca
    pdf.set_text_color(*branco)
    pdf.set_font("Arial", "B", 23)

    pdf.set_y(9)
    pdf.cell(
        0,
        10,
        "BIBLIOTECA",
        align="C",
        ln=True
    )

    # Subtítulo
    pdf.set_font("Arial", "", 10)

    pdf.cell(
        0,
        7,
        "Relatório de livros cadastrados",
        align="C",
        ln=True
    )

    # Volta para preto
    pdf.set_text_color(*preto)

    pdf.set_y(53)

    # --------------------------------------------------
    # INFORMAÇÕES DO RELATÓRIO
    # --------------------------------------------------

    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

    pdf.set_font("Arial", "B", 13)

    pdf.cell(
        0,
        8,
        "Relatório de Livros",
        ln=True
    )

    pdf.set_font("Arial", "", 9)

    pdf.set_text_color(*cinza)

    pdf.cell(
        0,
        6,
        f"Gerado em {data_atual}",
        ln=True
    )

    pdf.set_text_color(*preto)

    pdf.ln(7)

    # --------------------------------------------------
    # TABELA
    # --------------------------------------------------

    largura_id = 18
    largura_titulo = 72
    largura_autor = 65
    largura_ano = 25

    # Cabeçalho da tabela
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*branco)
    pdf.set_fill_color(*azul_marinho)

    pdf.cell(
        largura_id,
        11,
        "ID",
        border=0,
        align="C",
        fill=True
    )

    pdf.cell(
        largura_titulo,
        11,
        "Título",
        border=0,
        align="L",
        fill=True
    )

    pdf.cell(
        largura_autor,
        11,
        "Autor",
        border=0,
        align="L",
        fill=True
    )

    pdf.cell(
        largura_ano,
        11,
        "Ano",
        border=0,
        align="C",
        fill=True
    )

    pdf.ln()

    # --------------------------------------------------
    # DADOS DOS LIVROS
    # --------------------------------------------------

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*preto)

    for i, livro in enumerate(livros):

        id_livro = str(livro[0])
        titulo = str(livro[1])
        autor = str(livro[2])
        ano = str(livro[3])

        # Linhas alternadas
        if i % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(*branco)

        pdf.cell(
            largura_id,
            10,
            id_livro,
            border="B",
            align="C",
            fill=True
        )

        pdf.cell(
            largura_titulo,
            10,
            titulo[:42],
            border="B",
            align="L",
            fill=True
        )

        pdf.cell(
            largura_autor,
            10,
            autor[:38],
            border="B",
            align="L",
            fill=True
        )

        pdf.cell(
            largura_ano,
            10,
            ano,
            border="B",
            align="C",
            fill=True
        )

        pdf.ln()

    # --------------------------------------------------
    # TOTAL DE LIVROS
    # --------------------------------------------------

    contador_livros = len(livros)

    pdf.ln(12)

    pdf.set_fill_color(*azul_claro)
    pdf.set_draw_color(*azul_marinho)

    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*azul_marinho)

    pdf.cell(
        0,
        14,
        f"Total de livros cadastrados: {contador_livros}",
        border=1,
        align="C",
        fill=True
    )

    # --------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------

    pdf.set_y(-20)

    pdf.set_draw_color(*azul_marinho)

    pdf.line(
        15,
        pdf.get_y(),
        195,
        pdf.get_y()
    )

    pdf.ln(3)

    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(*cinza)

    pdf.cell(
        95,
        8,
        "Sistema de Biblioteca",
        align="L"
    )

    pdf.cell(
        95,
        8,
        f"Página {pdf.page_no()}",
        align="R"
    )

    # --------------------------------------------------
    # SALVAR PDF
    # --------------------------------------------------

    pdf_path = "relatorio_livros.pdf"

    pdf.output(pdf_path)

    return send_file(
        pdf_path,
        as_attachment=True,
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(debug=True)