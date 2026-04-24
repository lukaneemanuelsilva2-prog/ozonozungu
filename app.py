import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ozonozungu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs('static/uploads', exist_ok=True)

db = SQLAlchemy(app)

# MODELO - tabela de anúncios
class Anuncio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    contacto = db.Column(db.String(50), nullable=False)
    imagem = db.Column(db.String(200), nullable=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)

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
    return render_template('index.html', anuncios=anuncios, categoria_actual=categoria, pesquisa=pesquisa)

@app.route('/publicar', methods=['GET', 'POST'])
def publicar():
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
            imagem=imagem_nome
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('publicar.html')

@app.route('/anuncio/<int:id>')
def anuncio(id):
    anuncio = Anuncio.query.get_or_404(id)
    return render_template('anuncio.html', anuncio=anuncio)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True) 