from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, ContratoMensalista, Cliente, Pagamento, PlanoMensalista
from datetime import datetime

mensalistas_bp = Blueprint('mensalistas', __name__, url_prefix='/mensalistas')

@mensalistas_bp.route('/')
@login_required
def index():
    filtro = request.args.get('filtro', 'todos')
    hoje = datetime.now()
    mes, ano = hoje.month, hoje.year

    contratos = ContratoMensalista.query.filter(
        ContratoMensalista.cliente_id.isnot(None), 
        ContratoMensalista.status == 'ativo'
    ).all()

    resultado = []
    for c in contratos:
        pagamento = c.mensalidade_mes(mes, ano)
        status_pgto = 'pago' if pagamento and pagamento.status == 'pago' else 'pendente'
        
        if filtro == 'ativos' and status_pgto != 'pago': continue
        if filtro == 'pendentes' and status_pgto != 'pendente': continue
            
        resultado.append({'contrato': c, 'status_pgto': status_pgto})

    return render_template('mensalistas/index.html', resultado=resultado, filtro=filtro, mes=mes, ano=ano)

@mensalistas_bp.route('/cobrar/<int:contrato_id>', methods=['POST'])
@login_required
def cobrar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    hoje = datetime.now()
    pagamento = Pagamento(cliente_id=contrato.cliente_id, contrato_id=contrato.id, tipo='mensalidade',
                          valor=contrato.plano.valor_mensal, forma='pix', status='pago',
                          mes_referencia=f"{hoje.year}-{hoje.month:02d}")
    db.session.add(pagamento)
    db.session.commit()
    flash(f'Pagamento de {contrato.cliente.nome} registrado!', 'success')
    return redirect(url_for('mensalistas.index'))

# --- NOVAS ROTAS DE MANUTENÇÃO ---

@mensalistas_bp.route('/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    planos = PlanoMensalista.query.all()

    if request.method == 'POST':
        contrato.plano_id = request.form.get('plano_id')
        contrato.frequencia = request.form.get('frequencia')
        contrato.dia_semana = request.form.get('dia_semana')
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fim_str = request.form.get('hora_fim')

        if hora_inicio_str and hora_fim_str:
            contrato.hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
            contrato.hora_fim = datetime.strptime(hora_fim_str, '%H:%M').time()

        db.session.commit()
        flash('Contrato atualizado com sucesso!', 'success')
        # Volta para a ficha do cliente usando a nossa rota blindada
        return redirect(f"/clientes/{contrato.cliente_id}")

    return render_template('mensalistas/editar.html', contrato=contrato, planos=planos)


@mensalistas_bp.route('/<int:contrato_id>/cancelar', methods=['POST'])
@login_required
def cancelar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    # Regra de Ouro: Nunca deletar. Apenas mudar o status para liberar a agenda!
    contrato.status = 'cancelado' 
    db.session.commit()
    flash('Plano cancelado com sucesso. A quadra foi liberada.', 'success')
    return redirect(f"/clientes/{contrato.cliente_id}")