from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Configuracao, PlanoMensalista

ajustes_bp = Blueprint('ajustes', __name__, url_prefix='/ajustes')

@ajustes_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # 1. Salva os Horários
        hora_abertura = request.form.get('hora_abertura')
        hora_fechamento = request.form.get('hora_fechamento')
        if hora_abertura:
            Configuracao.set('hora_abertura', hora_abertura, 'Horário de abertura da Arena')
        if hora_fechamento:
            Configuracao.set('hora_fechamento', hora_fechamento, 'Horário de fechamento da Arena')

        # 2. Salva os Preços Avulsos (1h, 1h30, 2h)
        val_1h = request.form.get('valor_avulso_1h')
        val_1h30 = request.form.get('valor_avulso_1h30')
        val_2h = request.form.get('valor_avulso_2h')

        if val_1h: Configuracao.set('valor_avulso_1h', val_1h.replace(',', '.'), 'Valor Avulso 1h')
        if val_1h30: Configuracao.set('valor_avulso_1h30', val_1h30.replace(',', '.'), 'Valor Avulso 1h30')
        if val_2h: Configuracao.set('valor_avulso_2h', val_2h.replace(',', '.'), 'Valor Avulso 2h')

        # 3. Salva os Preços dos Mensalistas
        for nome in ['1h', '1h30', '2h']:
            valor_str = request.form.get(f'valor_mensal_{nome}')
            if valor_str:
                plano = PlanoMensalista.query.filter_by(nome=nome).first()
                if plano:
                    plano.valor_mensal = float(valor_str.replace(',', '.'))
        
        db.session.commit()
        flash('Configurações do sistema atualizadas!', 'success')
        return redirect(url_for('ajustes.index'))

    # Carrega as configurações de Horário e Avulsos
    configs = {
        'hora_abertura': Configuracao.get('hora_abertura', '8'),
        'hora_fechamento': Configuracao.get('hora_fechamento', '23'),
        'valor_avulso_1h': Configuracao.get('valor_avulso_1h', '150.00'),
        'valor_avulso_1h30': Configuracao.get('valor_avulso_1h30', '200.00'),
        'valor_avulso_2h': Configuracao.get('valor_avulso_2h', '250.00')
    }

    # Carrega os Planos Mensalistas do banco
    planos_db = PlanoMensalista.query.all()
    planos = {p.nome: p.valor_mensal for p in planos_db}

    return render_template('ajustes/index.html', configs=configs, planos=planos)