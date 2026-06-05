import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kitandadeal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'kitandadeal_secret_2025'
os.makedirs('static/uploads', exist_ok=True)

ADMIN_EMAIL = 'lukaneemanuelsilva2@gmail.com'

db = SQLAlchemy(app)

class Utilizador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    anuncios = db.relationship('Anuncio', backref='dono', lazy=True)

class Anuncio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    contacto = db.Column(db.String(50), nullable=False)
    imagem = db.Column(db.String(200), nullable=True)
    vendido = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    utilizador_id = db.Column(db.Integer, db.ForeignKey('utilizador.id'), nullable=False)

class AnuncioOculto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilizador_id = db.Column(db.Integer, db.ForeignKey('utilizador.id'), nullable=False)
    anuncio_id = db.Column(db.Integer, db.ForeignKey('anuncio.id'), nullable=False)

CATEGORIAS = [
    ('electronica', 'Electrónica'),
    ('automotivo', 'Automotivo'),
    ('roupas-femininas', 'Roupas femininas'),
    ('roupas-masculinas', 'Roupas masculinas'),
    ('imoveis', 'Imóveis'),
    ('mobilia', 'Mobília'),
    ('ferramentas', 'Ferramentas e Casa'),
    ('sapatos', 'Sapatos'),
    ('beleza', 'Beleza e Saúde'),
    ('brinquedos', 'Brinquedos e jogos'),
    ('desporto', 'Desporto'),
    ('joias', 'Joias e acessórios'),
    ('bolsas', 'Bolsas e malas'),
    ('bebe', 'Bebé e Maternidade'),
    ('artes', 'Artes e artesanato'),
    ('motas', 'Motas e motorizados'),
    ('jardim', 'Jardim e exterior'),
    ('escolar', 'Material escolar'),
    ('animais', 'Animais de estimação'),
    ('servicos', 'Serviços'),
    ('outros', 'Outros'),
]

def is_admin():
    if 'utilizador_id' not in session:
        return False
    u = Utilizador.query.get(session['utilizador_id'])
    return u and u.email == ADMIN_EMAIL

@app.route('/')
def index():
    categoria = request.args.get('categoria', '')
    pesquisa = request.args.get('pesquisa', '')
    query = Anuncio.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    if pesquisa:
        query = query.filter(Anuncio.titulo.ilike(f'%{pesquisa}%'))
    if 'utilizador_id' in session:
        ocultos = [o.anuncio_id for o in AnuncioOculto.query.filter_by(utilizador_id=session['utilizador_id']).all()]
        if ocultos:
            query = query.filter(~Anuncio.id.in_(ocultos))
    anuncios = query.order_by(Anuncio.data.desc()).all()
    return render_template('index.html', anuncios=anuncios, categoria_actual=categoria, pesquisa=pesquisa, categorias=CATEGORIAS, admin=is_admin())

@app.route('/registar', methods=['GET', 'POST'])
def registar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        password = request.form['password']
        if Utilizador.query.filter_by(email=email).first():
            flash('email_existe')
            return redirect(url_for('registar'))
        novo = Utilizador(nome=nome, email=email, password=generate_password_hash(password))
        db.session.add(novo)
        db.session.commit()
        session['utilizador_id'] = novo.id
        session['utilizador_nome'] = novo.nome
        return redirect(url_for('index'))
    return render_template('registar.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        utilizador = Utilizador.query.filter_by(email=email).first()
        if not utilizador:
            flash('email_nao_existe')
            return redirect(url_for('login'))
        if not check_password_hash(utilizador.password, password):
            flash('password_errada')
            return redirect(url_for('login'))
        session['utilizador_id'] = utilizador.id
        session['utilizador_nome'] = utilizador.nome
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/publicar', methods=['GET', 'POST'])
def publicar():
    if 'utilizador_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        imagem_nome = None
        if 'imagem' in request.files:
            file = request.files['imagem']
            if file.filename != '':
                imagem_nome = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_nome))
        novo = Anuncio(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            preco=request.form['preco'],
            categoria=request.form['categoria'],
            contacto=request.form['contacto'],
            imagem=imagem_nome,
            utilizador_id=session['utilizador_id']
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('publicar.html', categorias=CATEGORIAS)

@app.route('/anuncio/<int:id>')
def anuncio(id):
    anuncio = Anuncio.query.get_or_404(id)
    dono = session.get('utilizador_id') == anuncio.utilizador_id
    return render_template('anuncio.html', anuncio=anuncio, dono=dono, admin=is_admin())

@app.route('/apagar/<int:id>', methods=['POST'])
def apagar(id):
    anuncio = Anuncio.query.get_or_404(id)
    if session.get('utilizador_id') != anuncio.utilizador_id and not is_admin():
        return redirect(url_for('index'))
    db.session.delete(anuncio)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/vendido/<int:id>', methods=['POST'])
def vendido(id):
    anuncio = Anuncio.query.get_or_404(id)
    if session.get('utilizador_id') != anuncio.utilizador_id:
        return redirect(url_for('anuncio', id=id))
    anuncio.vendido = True
    db.session.commit()
    return redirect(url_for('anuncio', id=id))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    anuncio = Anuncio.query.get_or_404(id)
    if session.get('utilizador_id') != anuncio.utilizador_id:
        return redirect(url_for('index'))
    if request.method == 'POST':
        anuncio.titulo = request.form['titulo']
        anuncio.descricao = request.form['descricao']
        anuncio.categoria = request.form['categoria']
        anuncio.contacto = request.form['contacto']
        if 'imagem' in request.files:
            file = request.files['imagem']
            if file.filename != '':
                imagem_nome = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_nome))
                anuncio.imagem = imagem_nome
        db.session.commit()
        return redirect(url_for('anuncio', id=id))
    return render_template('editar.html', anuncio=anuncio, categorias=CATEGORIAS)

@app.route('/ocultar/<int:id>', methods=['POST'])
def ocultar(id):
    if 'utilizador_id' not in session:
        return redirect(url_for('login'))
    ja_existe = AnuncioOculto.query.filter_by(
        utilizador_id=session['utilizador_id'],
        anuncio_id=id
    ).first()
    if not ja_existe:
        novo = AnuncioOculto(utilizador_id=session['utilizador_id'], anuncio_id=id)
        db.session.add(novo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/suporte')
def suporte():
    return redirect('https://wa.me/244952656994')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)


    #git init
    #git add .
    #git commit -m "primeiro commit"
    #git branch -M main
    #git remote add origin https://github.com/NOME-DE-UTILIZADOR/NOME-DO-REPOSITORIO.git
    #git push -u origin main