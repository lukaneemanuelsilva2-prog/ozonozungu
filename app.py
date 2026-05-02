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

CATEGORIAS = [
    ('📱', 'Electrónica'),
    ('🚗', 'Automotivo'),
    ('👗', 'Roupas femininas'),
    ('👕', 'Roupas masculinas'),
    ('🏠', 'Imóveis'),
    ('🛋️', 'Mobília'),
    ('🔧', 'Ferramentas e Casa'),
    ('👟', 'Sapatos'),
    ('💄', 'Beleza e Saúde'),
    ('🧸', 'Brinquedos e jogos'),
    ('🏋️', 'Desporto'),
    ('💍', 'Joias e acessórios'),
    ('👜', 'Bolsas e malas'),
    ('🍼', 'Bebé e Maternidade'),
    ('🎨', 'Artes e artesanato'),
    ('🏍️', 'Motas e motorizados'),
    ('🌿', 'Jardim e exterior'),
    ('📚', 'Material escolar'),
    ('🐾', 'Animais de estimação'),
    ('⚙️', 'Serviços'),
    ('🛒', 'Outros'),
]

@app.route('/')
def index():
    categoria = request.args.get('categoria', '')
    pesquisa = request.args.get('pesquisa', '')
    query = Anuncio.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    if pesquisa:
        query = query.filter(Anuncio.titulo.ilike(f'%{pesquisa}%'))
    anuncios = query.order_by(Anuncio.data.desc()).all()
    return render_template('index.html', anuncios=anuncios, categoria_actual=categoria, pesquisa=pesquisa, categorias=CATEGORIAS)

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
    return render_template('anuncio.html', anuncio=anuncio, dono=dono)

@app.route('/apagar/<int:id>', methods=['POST'])
def apagar(id):
    anuncio = Anuncio.query.get_or_404(id)
    if session.get('utilizador_id') != anuncio.utilizador_id:
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
        anuncio.preco = request.form['preco']
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

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)