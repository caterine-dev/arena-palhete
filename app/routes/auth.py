from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('agenda.index'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('agenda.index'))

    if request.method == 'POST':
        # Pegamos o valor do input (que no HTML ainda tem o name="email")
        acesso_digitado = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar') == 'on'

        # Busca o usuário pelo e-mail OU pelo nome, desde que esteja ativo
        usuario = Usuario.query.filter(
            ((Usuario.email == acesso_digitado) | (Usuario.nome == acesso_digitado)),
            Usuario.ativo == True
        ).first()

        if usuario and usuario.check_senha(senha):
            login_user(usuario, remember=lembrar)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('agenda.index'))
        else:
            flash('E-mail, usuário ou senha incorretos.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))