from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Usuario

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

@usuarios_bp.route('/')
@login_required
def index():
    # Trava de segurança: Apenas gerentes podem ver a equipe
    if not current_user.is_gerente():
        flash('Acesso restrito para Gerentes.', 'error')
        return redirect(url_for('agenda.index'))
    
    usuarios = Usuario.query.all()
    return render_template('usuarios/index.html', usuarios=usuarios)

@usuarios_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if not current_user.is_gerente():
        return redirect(url_for('agenda.index'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        perfil = request.form.get('perfil', 'funcionario')

        # Verifica se o email já existe para não dar erro no banco
        if Usuario.query.filter_by(email=email).first():
            flash('Este email (login) já está em uso por outro funcionário.', 'error')
            return redirect(url_for('usuarios.novo'))

        novo_usuario = Usuario(nome=nome, email=email, perfil=perfil)
        novo_usuario.set_senha(senha) # Criptografa a senha imediatamente
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Funcionário cadastrado com sucesso!', 'success')
        return redirect(url_for('usuarios.index'))

    return render_template('usuarios/novo.html')

@usuarios_bp.route('/<int:usuario_id>/status', methods=['POST'])
@login_required
def toggle_status(usuario_id):
    if not current_user.is_gerente():
        return redirect(url_for('agenda.index'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Trava: O gerente não pode desativar a si mesmo e trancar o sistema
    if usuario.id == current_user.id:
        flash('Você não pode desativar o seu próprio usuário logado.', 'error')
    else:
        usuario.ativo = not usuario.ativo
        db.session.commit()
        status_msg = 'ativado' if usuario.ativo else 'desativado (sem acesso)'
        flash(f'Acesso do funcionário {status_msg}.', 'success')
    
    return redirect(url_for('usuarios.index'))