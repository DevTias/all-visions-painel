/* ALL VISIONS · painel da festa */
(() => {
  'use strict';
  const { esc, fmt, api, ingresso } = window.AV;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // um tom por lote, na ordem da escada (uma cor so, do claro ao escuro)
  const TONS = ['#b7cead', '#93b287', '#6f9163', '#4f6d45', '#3a5132', '#2d3f26'];
  const tom = (i) => TONS[Math.min(i, TONS.length - 1)];
  const pl = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

  let CFG = null;
  let pulso = null;
  let assinatura = '';
  let ultimaVenda = null;
  const estreia = { casa: true, feed: false };  // a casa acende lugar por lugar so na primeira vez
  const estado = {
    pedidos: { status: '', busca: '' },
    segmento: 'Compradores',
    buscaContato: '',
    objetivo: 'virada',
    roteiro: { lotacao: 45, energia: 3, hora: '00:30', votos: true },
    previa: null,
  };

  // ------------------------------------------------------------ base

  function avisar(texto, erro = false) {
    const el = $('#aviso');
    el.textContent = texto;
    el.className = 'aviso visivel' + (erro ? ' erro' : '');
    clearTimeout(avisar.t);
    avisar.t = setTimeout(() => (el.className = 'aviso'), 4200);
  }

  function palco(html) {
    $('#palco').innerHTML = html;
  }

  function janela(html) {
    const d = $('#janela');
    d.innerHTML = html;
    if (!d.open) d.showModal();
    return d;
  }

  function confirmar(titulo, texto, rotulo = 'Confirmar') {
    return new Promise((resolve) => {
      const d = janela(`
        <h3>${esc(titulo)}</h3>
        <p>${esc(texto)}</p>
        <div class="janela-acoes">
          <button class="botao fantasma" value="nao">Voltar</button>
          <button class="botao" value="sim">${esc(rotulo)}</button>
        </div>`);
      d.onclick = (e) => {
        const b = e.target.closest('button[value]');
        if (!b) return;
        d.onclick = null;
        d.close();
        resolve(b.value === 'sim');
      };
    });
  }

  const cabeca = (titulo, linha, extra = '') => `
    <header class="cabeca">
      <div>
        <h1>${titulo}</h1>
        <p class="cabeca-linha">${linha}</p>
      </div>
      ${extra ? `<div class="cabeca-acoes">${extra}</div>` : ''}
    </header>`;

  const nota = (texto) => `<p class="nota">${texto}</p>`;

  const NIVEL = { alto: 'Alto', medio: 'Médio', baixo: 'Baixo' };
  const TOM = { atencao: 'Atenção', oportunidade: 'Oportunidade', ok: 'Em ordem', neutro: 'Manter' };
  const STATUS_LOTE = { aguardando: 'Aguardando', ativo: 'Em venda', esgotado: 'Esgotado', pausado: 'Pausado' };
  const STATUS_AUTO = { rascunho: 'Rascunho', agendada: 'Agendada', ativa: 'Sempre ligada', enviada: 'Enviada', pausada: 'Pausada' };
  const METODO = { pix: 'Pix', cartao: 'Cartão', dinheiro: 'Dinheiro', cortesia: 'Cortesia' };

  const marca = (classe, texto) => `<span class="marca-st ${classe}">${esc(texto)}</span>`;

  function dMenos(iso, festa) {
    if (!iso || !festa) return '';
    const d = Math.round((new Date(festa + 'T12:00') - new Date(iso.slice(0, 10) + 'T12:00')) / 864e5);
    return d === 0 ? 'Dia da festa' : d > 0 ? `D-${d}` : `D+${-d}`;
  }

  // ------------------------------------------------------------ graficos

  function graficoRitmo(m, ed) {
    if (!ed.abertura_vendas) return '';
    const W = 780, L = 34, R = 46, T = 14, B = 190, BASE = 262, ALT = 40;
    const total = m.dias_de_venda + 1;
    const cap = m.capacidade;
    const idx = (iso) => Math.round((new Date(iso + 'T12:00') - new Date(ed.abertura_vendas + 'T12:00')) / 864e5);
    const X = (i) => L + (i / total) * (W - L - R);
    const Y = (v) => B - (v / cap) * (B - T);
    const real = m.serie.filter((p) => idx(p.dia) >= 0).map((p) => ({ i: idx(p.dia) + 1, v: p.acumulado, n: p.ingressos, dia: p.dia }));
    const proj = m.projecao.pontos.map((p) => ({ i: idx(p.dia) + 1, v: p.acumulado, dia: p.dia })).filter((p) => p.i <= total);
    const ultimo = real[real.length - 1];
    const fimProj = proj[proj.length - 1];
    const maxDia = Math.max(1, ...real.map((p) => p.n));
    const slot = (W - L - R) / total;

    const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => {
      const v = Math.round(cap * f);
      return `<line class="g-grade" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text class="g-eixo" x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`;
    }).join('');

    const ticks = [];
    for (let i = 0; i < total; i += 7) ticks.push(i);
    if (ticks[ticks.length - 1] !== total - 1) ticks.push(total - 1);
    const dataDe = (i) => {
      const d = new Date(ed.abertura_vendas + 'T12:00');
      d.setDate(d.getDate() + i);
      return d.toISOString().slice(0, 10);
    };
    const eixoX = ticks.map((i) => `<text class="g-eixo" x="${X(i) + slot / 2}" y="${BASE + 18}" text-anchor="middle">${i === total - 1 ? 'festa' : fmt.dia(dataDe(i))}</text>`).join('');

    const caminhoReal = real.length ? `M${X(0)} ${Y(0)} ` + real.map((p) => `L${X(p.i)} ${Y(p.v)}`).join(' ') : '';
    const area = real.length ? `${caminhoReal} L${X(ultimo.i)} ${Y(0)} Z` : '';
    const caminhoProj = ultimo && proj.length ? `M${X(ultimo.i)} ${Y(ultimo.v)} ` + proj.map((p) => `L${X(p.i)} ${Y(p.v)}`).join(' ') : '';

    const barras = real.map((p) => {
      const h = Math.max((p.n / maxDia) * ALT, p.n ? 2 : 0);
      return `<rect class="g-barra" x="${X(p.i - 1) + 1}" y="${BASE - h}" width="${Math.max(slot - 2, 2)}" height="${h}" rx="2"/>`;
    }).join('');

    const colunas = [...real.map((p) => ({ ...p, tipo: 'real' })), ...proj.map((p) => ({ ...p, tipo: 'proj' }))].map((p) => {
      const dica = p.tipo === 'real'
        ? `${fmt.dia(p.dia)}: ${p.v} vendidos, ${p.n} no dia`
        : `${fmt.dia(p.dia)}: projeção de ${fmt.n(p.v)}`;
      return `<g class="g-col" data-dica="${esc(dica)}">
        <rect class="g-alvo" x="${X(p.i - 1)}" y="${T}" width="${slot}" height="${BASE - T}"/>
        <line class="g-mira" x1="${X(p.i)}" x2="${X(p.i)}" y1="${T}" y2="${B}"/>
        <circle class="g-ponto" cx="${X(p.i)}" cy="${Y(p.v)}" r="4"/>
      </g>`;
    }).join('');

    return `
      <div class="legenda">
        <span><i class="l-linha"></i>Vendido</span>
        <span><i class="l-linha tracejada"></i>Projeção</span>
        <span><i class="l-linha fina"></i>Ritmo para lotar</span>
      </div>
      <svg class="grafico" viewBox="0 0 ${W} ${BASE + 26}" role="img" aria-label="Ingressos vendidos por dia, projeção e ritmo necessário para lotar a casa">
        <defs><linearGradient id="g-fundo" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#b7cead" stop-opacity=".22"/><stop offset="1" stop-color="#b7cead" stop-opacity="0"/></linearGradient></defs>
        ${grade}
        <line class="g-meta" x1="${X(0)}" y1="${Y(0)}" x2="${X(total)}" y2="${Y(cap)}"/>
        ${area ? `<path class="g-area" d="${area}"/>` : ''}
        ${caminhoProj ? `<path class="g-proj" d="${caminhoProj}"/>` : ''}
        ${caminhoReal ? `<path class="g-real" d="${caminhoReal}"/>` : ''}
        ${ultimo ? `<line class="g-hoje" x1="${X(ultimo.i)}" x2="${X(ultimo.i)}" y1="${Y(ultimo.v)}" y2="${BASE}"/>
          <circle class="g-marco" cx="${X(ultimo.i)}" cy="${Y(ultimo.v)}" r="4.5"/>
          <text class="g-rotulo" x="${X(ultimo.i) - 8}" y="${Y(ultimo.v) - 10}" text-anchor="end">${ultimo.v} hoje</text>` : ''}
        ${fimProj && ultimo ? `<text class="g-rotulo suave" x="${X(fimProj.i) + 6}" y="${Y(fimProj.v) + 4}">${Math.round(fimProj.v)}</text>` : ''}
        <text class="g-eixo" x="${L}" y="${BASE - ALT - 8}">por dia</text>
        <line class="g-grade" x1="${L}" x2="${W - R}" y1="${BASE}" y2="${BASE}"/>
        ${barras}
        ${eixoX}
        ${colunas}
      </svg>
      <details class="numeros">
        <summary>Ver os números</summary>
        <table class="tabela compacta"><thead><tr><th>Dia</th><th class="num">No dia</th><th class="num">Acumulado</th></tr></thead>
        <tbody>${real.map((p) => `<tr><td>${fmt.dia(p.dia)}</td><td class="num">${p.n}</td><td class="num">${p.v}</td></tr>`).join('')}</tbody></table>
      </details>`;
  }

  function casa(lotes, cap, acender = false) {
    const lugares = [];
    const por = (classe, estilo, dica) => lugares.push(`<i class="lugar ${classe}" style="--i:${lugares.length};${estilo}" data-dica="${esc(dica)}"></i>`);
    lotes.forEach((l, i) => { for (let k = 0; k < l.vendidos; k++) por('v', `--tom:${tom(i)}`, `${l.nome}, vendido`); });
    lotes.forEach((l) => { for (let k = 0; k < l.reservados; k++) por('r', '', `${l.nome}, aguardando pagamento`); });
    lotes.forEach((l) => { for (let k = 0; k < (l.disponivel || 0); k++) por('', '', `${l.nome}, livre`); });
    while (lugares.length < cap) por('fora', '', 'Lugar ainda sem lote');
    const legenda = lotes.filter((l) => l.quantidade).map((l, i) =>
      `<span><i class="l-quadro" style="--tom:${tom(i)}"></i>${esc(l.nome)} <b>${l.vendidos}/${l.quantidade}</b></span>`).join('');
    return `<div class="casa ${acender ? 'estreia' : ''}">${lugares.slice(0, cap).join('')}</div><div class="legenda quebra">${legenda}</div>`;
  }

  function escada(lotes) {
    const ls = lotes.filter((l) => l.quantidade);
    if (!ls.length) return '<p class="vazio">Nenhum lote criado. Use o formulário abaixo para montar o primeiro degrau.</p>';
    const W = 780, H = 250, L = 46, R = 10, T = 34, B = 220;
    const total = ls.reduce((s, l) => s + l.quantidade, 0);
    const pmax = Math.max(...ls.map((l) => l.preco));
    const teto = Math.max(Math.ceil(pmax / 50) * 50, 50);
    const Y = (p) => B - (p / teto) * (B - T);
    let acc = 0;
    const degraus = ls.map((l) => {
      const i = lotes.indexOf(l);
      const x0 = L + (acc / total) * (W - L - R);
      const w = (l.quantidade / total) * (W - L - R);
      const wv = w * (l.vendidos / l.quantidade);
      const wr = w * (l.reservados / l.quantidade);
      const y = Y(l.preco);
      const h = B - y;
      acc += l.quantidade;
      const dica = `${l.nome}, ${fmt.brl(l.preco)}: ${l.vendidos} vendidos, ${l.reservados} reservados, ${l.disponivel} livres. Rende ${fmt.brl(l.preco * l.quantidade)} se esgotar.`;
      return `<g data-dica="${esc(dica)}">
        <rect class="e-degrau" x="${x0 + 1}" y="${y}" width="${Math.max(w - 2, 1)}" height="${h}"/>
        ${wv > 0 ? `<rect x="${x0 + 1}" y="${y}" width="${Math.max(wv - (wv >= w ? 2 : 0), 1)}" height="${h}" fill="${tom(i)}"/>` : ''}
        ${wr > 0 ? `<rect x="${x0 + 1 + wv}" y="${y}" width="${Math.max(wr - 1, 1)}" height="${h}" fill="url(#e-risco)"/>` : ''}
        <text class="g-rotulo" x="${x0 + 6}" y="${y - 20}">${esc(l.nome)}</text>
        <text class="g-eixo forte" x="${x0 + 6}" y="${y - 6}">${fmt.brl(l.preco)}</text>
        <text class="g-eixo" x="${x0 + w - 4}" y="${B + 16}" text-anchor="end">${acc}</text>
      </g>`;
    }).join('');
    const grade = Array.from({ length: teto / 50 + 1 }, (_, k) => k * 50).map((p) =>
      `<line class="g-grade" x1="${L}" x2="${W - R}" y1="${Y(p)}" y2="${Y(p)}"/><text class="g-eixo" x="${L - 8}" y="${Y(p) + 4}" text-anchor="end">${p}</text>`).join('');
    return `
      <div class="legenda">
        <span><i class="l-quadro" style="--tom:${tom(1)}"></i>Vendido</span>
        <span><i class="l-quadro risco"></i>Aguardando pagamento</span>
        <span><i class="l-quadro vago"></i>Livre</span>
      </div>
      <svg class="grafico" viewBox="0 0 ${W} ${H}" role="img" aria-label="Escada de lotes: largura é a quantidade, altura é o preço">
        <defs><pattern id="e-risco" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#b7cead" stroke-width="1.4" opacity=".55"/></pattern></defs>
        ${grade}
        <text class="g-eixo" x="${L - 8}" y="${T - 14}" text-anchor="end">R$</text>
        ${degraus}
        <text class="g-eixo" x="${L}" y="${B + 16}">0</text>
      </svg>`;
  }

  const barras = (lista, limite = 6) => `
    <div class="barras">${lista.slice(0, limite).map((x) => `
      <div class="barra-linha" data-dica="${esc(x.rotulo)}: ${pl(x.n, 'pessoa', 'pessoas')}">
        <span class="barra-rotulo">${esc(x.rotulo)}</span>
        <span class="barra-trilho"><i style="width:${x.pct}%"></i></span>
        <span class="barra-valor">${x.pct}%</span>
      </div>`).join('')}</div>`;

  function horas(lista) {
    if (!lista.length) return '';
    const max = Math.max(1, ...lista.map((h) => h.n));
    const pico = lista.reduce((a, b) => (b.n > a.n ? b : a));
    return `<div class="horas">${lista.map((h) => `
      <div class="hora-col ${h === pico ? 'pico' : ''}" data-dica="${h.hora}h: ${pl(h.n, 'pedido', 'pedidos')}">
        <i style="height:${(h.n / max) * 100}%"></i>
        <span>${h.hora % 6 === 0 || h === pico ? h.hora + 'h' : ''}</span>
      </div>`).join('')}</div>`;
  }

  // ------------------------------------------------------------ rodape do trilho

  function trilhoPe() {
    const ed = CFG.edicao;
    const dias = Math.round((new Date(ed.data + 'T12:00') - new Date(CFG.agora.slice(0, 10) + 'T12:00')) / 864e5);
    const ensaio = CFG.modo === 'ensaio';
    $('#trilho-pe').innerHTML = `
      <p class="pe-contagem"><strong>${dias >= 0 ? dias : 0}</strong><span>${dias === 1 ? 'dia' : 'dias'} até<br>${fmt.ponto(ed.data)}</span></p>
      <div class="pe-modo">
        <p>${ensaio ? `<b>Ensaio.</b> Vendas, promoters e compradores são simulados. Relógio parado em ${fmt.dia(CFG.agora)}.` : '<b>Dados reais.</b> Relógio de hoje.'}</p>
        <button class="elo" data-acao="modo" data-modo="${ensaio ? 'real' : 'ensaio'}">${ensaio ? 'Começar do zero' : 'Voltar ao ensaio'}</button>
      </div>`;
  }

  // ------------------------------------------------------------ 1. panorama

  const assinar = (d) => [d.metricas.vendidos, d.metricas.reservados, d.ultimas[0]?.id, d.entradas, d.riscos.length, d.tarefas.length, d.proximas.length].join('|');

  async function panorama() {
    const d = await api('/api/painel');
    const { metricas: m, edicao: ed, lotes } = d;
    assinatura = assinar(d);
    const abriu = m.dias_ate_abertura === 0;
    const risco = d.riscos[0];
    const frase = !abriu
      ? `As vendas abrem em ${m.dias_ate_abertura} dias. Até lá, o trabalho é montar a escada de lotes e aquecer o olhar de quem está de fora.`
      : !m.vendidos ? 'Vendas abertas. O primeiro ingresso ainda não saiu.'
        : risco ? risco.leitura : 'Nenhum ponto cego hoje. A venda segue no ritmo de lotar a casa.';
    const ref = m.referencia;
    const manchete = !abriu ? 'A porta ainda está fechada' : !m.vendidos ? 'Vendas abertas' : risco ? risco.titulo : 'A casa enche no ritmo certo';
    const quando = fmt.extenso(ed.data);
    const novo = estreia.feed;
    estreia.feed = false;

    palco(`
      ${cabeca(esc(ed.nome), `${esc(ed.tema || '')}. ${quando.charAt(0).toUpperCase() + quando.slice(1)}, ${esc(ed.local || '')}.`,
        d.modo === 'ensaio' ? '<button class="botao fantasma" data-acao="venda-ensaio">Simular uma venda</button>' : '')}

      <section class="abre">
        <div>
          <h2 class="fala-titulo">${esc(manchete)}</h2>
          <p class="fala">${esc(frase)}</p>
          ${risco && abriu && m.vendidos ? '<a class="elo" href="#visoes">Ver o que fazer</a>' : !lotes.length ? '<a class="elo" href="#ingressos">Montar a escada de lotes</a>' : ''}
        </div>
        <div>
          <p class="casa-conta"><strong>${m.vendidos}</strong> de ${m.capacidade} lugares vendidos
            <span>${m.ocupacao}% da casa${m.reservados ? `, ${m.reservados} aguardando pagamento` : ''}</span></p>
          ${casa(lotes, m.capacidade, estreia.casa)}
        </div>
      </section>

      <section class="quadro q-panorama">
        <div class="cel cel-num">
          <p class="rotulo">Bilheteria</p>
          <p class="numero">${fmt.brl(m.receita)}</p>
          <p class="apoio">${m.cobertura_custo}% do que a 1.0 custou (${fmt.brl(ref.custo)})</p>
        </div>
        <div class="cel cel-num">
          <p class="rotulo">Ritmo, últimos 3 dias</p>
          <p class="numero">${fmt.n(m.ritmo_3d, 1)}<small> por dia</small></p>
          <p class="apoio">${m.dias_restantes ? `Para lotar, ${fmt.n(m.ritmo_necessario, 1)} por dia` : 'Venda encerrada'}</p>
        </div>
        <div class="cel cel-num">
          <p class="rotulo">Projeção de fechamento</p>
          <p class="numero">${m.projecao.central}<small> de ${m.capacidade}</small></p>
          <p class="apoio">Entre ${m.projecao.baixa} e ${m.projecao.alta}, conforme a última semana</p>
        </div>
        <div class="cel cel-num">
          <p class="rotulo">Ticket médio</p>
          <p class="numero">${fmt.brl(m.ticket_medio)}</p>
          <p class="apoio">Custo por pessoa na 1.0: ${fmt.brl(ref.custo_por_pessoa)}</p>
        </div>

        <div class="cel cel-grafico">
          <p class="rotulo">Venda dia a dia${m.dia_de_venda ? `<small>dia ${Math.min(m.dia_de_venda, m.dias_de_venda)} de ${m.dias_de_venda}</small>` : ''}</p>
          ${abriu ? graficoRitmo(m, ed) : `<p class="vazio">O gráfico começa em ${fmt.dia(ed.abertura_vendas)}, na abertura das vendas.</p>`}
        </div>
        <div class="cel cel-cegos">
          <p class="rotulo">Pontos cegos</p>
          ${d.riscos.length ? `<ul class="lista-cegos">${d.riscos.slice(0, 5).map((r) => `
            <li><span class="nivel ${r.nivel}">${NIVEL[r.nivel]}</span><a href="#visoes">${esc(r.titulo)}</a></li>`).join('')}</ul>` : '<p class="vazio">Nada fora do lugar.</p>'}
          ${d.riscos.length > 5 ? `<a class="elo" href="#visoes">Mais ${d.riscos.length - 5}</a>` : ''}
        </div>

        <div class="cel cel-feed">
          <p class="rotulo">Últimas vendas</p>
          ${d.ultimas.length ? `<ul class="feed">${d.ultimas.map((p, i) => `
            <li class="${p.status} ${novo && i === 0 ? 'novo' : ''}">
              <time>${fmt.diaHora(p.criado_em)}</time>
              <span class="feed-quem">${esc(p.comprador || 'Sem nome')}${p.promoter ? ` <em>via ${esc(p.promoter)}</em>` : ''}</span>
              <span class="feed-o-que">${p.quantidade} × ${esc(p.lote)}${p.status === 'pendente' ? ', pendente' : p.status === 'estornado' ? ', estornado' : ''}</span>
              <b>${fmt.brl(p.valor_total)}</b>
            </li>`).join('')}</ul>` : '<p class="vazio">Nenhuma venda registrada.</p>'}
        </div>
        <div class="cel cel-prox">
          <p class="rotulo">Próximos disparos</p>
          ${d.proximas.length ? `<ul class="agenda">${d.proximas.map((a) => `
            <li><time>${fmt.diaHora(a.agendado_para)}</time><span>${esc(a.titulo)}</span><small>${esc(a.canal || a.tipo)}</small></li>`).join('')}</ul>` : '<p class="vazio">Nada agendado.</p>'}
          <a class="elo" href="#automacao">Abrir a central</a>
        </div>
        <div class="cel cel-tarefas">
          <p class="rotulo">Tarefas abertas</p>
          ${d.tarefas.length ? `<ul class="agenda">${d.tarefas.map((t) => `
            <li class="${t.prazo && t.prazo < m.hoje ? 'vencida' : ''}"><time>${fmt.dia(t.prazo)}</time><span>${esc(t.titulo)}</span><small>${esc(t.responsavel || 'sem dono')}</small></li>`).join('')}</ul>` : '<p class="vazio">Tudo entregue.</p>'}
        </div>
      </section>`);
    estreia.casa = false;

    clearInterval(pulso);
    pulso = setInterval(async () => {
      if ((location.hash || '#panorama') !== '#panorama' || document.hidden || $('#janela').open) return;
      try {
        const n = await api('/api/painel');
        if (assinar(n) !== assinatura) {
          if (n.ultimas[0]?.id !== ultimaVenda) piscar();
          await redesenhar();
        }
      } catch (_) { /* servidor fora do ar: tenta de novo no proximo ciclo */ }
    }, 6000);
    ultimaVenda = d.ultimas[0]?.id;
  }

  // o olho pisca quando ve uma venda nova; a linha dela acende no feed
  function piscar() {
    const o = $('#olho-marca');
    o.classList.remove('viu');
    void o.getBoundingClientRect();
    o.classList.add('viu');
    estreia.feed = true;
  }

  // ------------------------------------------------------------ 2. ingressos

  async function ingressos() {
    const [lotes, pedidos, proms, entrada] = await Promise.all([
      api('/api/lotes'),
      api('/api/pedidos?' + new URLSearchParams(estado.pedidos)),
      api('/api/promoters'),
      api('/api/checkin'),
    ]);
    const hist = CFG.historico[0];
    const ativo = lotes.find((l) => l.status === 'ativo');
    const somaLotes = lotes.reduce((s, l) => s + (l.quantidade || 0), 0);
    const potencial = lotes.reduce((s, l) => s + (l.quantidade || 0) * l.preco, 0);
    const amostra = estado.previa || (pedidos.find((p) => p.codigos) || {}).codigos?.split(' ')[0] || null;

    palco(`
      ${cabeca('Ingressos', 'Lotes, vendas, e-tickets e portaria. A escada mostra onde está o dinheiro: largura é quantidade, altura é preço.')}

      <section class="quadro q-dois">
        <div class="cel largo">
          <p class="rotulo">Escada de lotes<small>${somaLotes} ingressos, ${fmt.brl(potencial)} se esgotar</small></p>
          ${escada(lotes)}
          ${nota('A área de cada degrau é o que ele rende. Um degrau estreito e alto esgota rápido e deixa dinheiro na mesa: foi o que aconteceu com o 3º lote da 1.0.')}
        </div>
        <div class="cel">
          <p class="rotulo">Referência: a escada da 1.0</p>
          ${hist ? `<ol class="ref-escada">${hist.lotes.map((l) => `<li><span>${esc(l.nome)}${l.descricao ? `<small>${esc(l.descricao)}</small>` : ''}</span><b>${fmt.brl(l.preco)}</b></li>`).join('')}</ol>
          <p class="apoio">${hist.publico_final} pessoas, casa cheia. As quantidades por lote não foram registradas.</p>` : ''}
        </div>

        <div class="cel total">
          <p class="rotulo">Lotes</p>
          <div class="rolagem"><table class="tabela">
            <thead><tr><th>Lote</th><th class="num">Preço (R$)</th><th class="num">Quantidade</th><th class="num">Vendidos</th><th class="num">Pendentes</th><th class="num">Livres</th><th>Situação</th><th></th></tr></thead>
            <tbody>${lotes.map((l, i) => `
              <tr>
                <td><i class="l-quadro" style="--tom:${tom(i)}"></i><input class="em-linha" aria-label="Nome do lote" value="${esc(l.nome)}" data-mudar="lote" data-id="${l.id}" data-campo="nome"></td>
                <td class="num"><input class="em-linha num" aria-label="Preço" type="number" min="0" step="5" value="${l.preco}" data-mudar="lote" data-id="${l.id}" data-campo="preco"></td>
                <td class="num"><input class="em-linha num" aria-label="Quantidade" type="number" min="1" value="${l.quantidade}" data-mudar="lote" data-id="${l.id}" data-campo="quantidade"></td>
                <td class="num">${l.vendidos}</td><td class="num">${l.reservados}</td><td class="num">${l.disponivel}</td>
                <td><select class="em-linha" aria-label="Situação" data-mudar="lote" data-id="${l.id}" data-campo="status">
                  ${Object.entries(STATUS_LOTE).map(([k, v]) => `<option value="${k}" ${k === l.status ? 'selected' : ''}>${v}</option>`).join('')}
                </select></td>
                <td class="acoes">${l.vendidos + l.reservados ? '' : `<button class="elo" data-acao="lote-apagar" data-id="${l.id}">Apagar</button>`}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>
          <form class="form-linha" data-form="lote">
            <label>Novo lote<input name="nome" placeholder="VIP, 4º lote, lista..." required></label>
            <label>Preço (R$)<input name="preco" type="number" min="0" step="5" required></label>
            <label>Quantidade<input name="quantidade" type="number" min="1" required></label>
            <label>Observação<input name="descricao" placeholder="opcional"></label>
            <button class="botao">Criar lote</button>
          </form>
          ${nota('Quando um lote esgota, o próximo abre sozinho e nasce a tarefa de anunciar a virada. Mudar preço só vale para vendas novas.')}
        </div>

        <div class="cel">
          <p class="rotulo">Registrar venda</p>
          <form class="form-coluna" data-form="venda">
            <label>Lote<select name="lote_id">${lotes.filter((l) => !['esgotado'].includes(l.status)).map((l) =>
              `<option value="${l.id}" ${ativo && l.id === ativo.id ? 'selected' : ''}>${esc(l.nome)}, ${fmt.brl(l.preco)} (${l.disponivel} livres)</option>`).join('')}</select></label>
            <label>Nome de quem compra<input name="nome" required autocomplete="off"></label>
            <label>Instagram<input name="instagram" placeholder="@" autocomplete="off"></label>
            <div class="par">
              <label>Quantidade<input name="quantidade" type="number" min="1" max="10" value="1"></label>
              <label>Código do promoter<input name="codigo" list="codigos" placeholder="opcional" autocomplete="off"></label>
            </div>
            <datalist id="codigos">${proms.promoters.filter((p) => p.ativo).map((p) => `<option value="${esc(p.codigo)}">${esc(p.nome)}</option>`).join('')}</datalist>
            <div class="par">
              <label>Forma<select name="metodo">${Object.entries(METODO).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></label>
              <label>Pagamento<select name="status"><option value="pago">Confirmado</option><option value="pendente">Pendente</option></select></label>
            </div>
            <button class="botao">Registrar venda</button>
          </form>
          ${nota('A transação aqui é um registro: nenhum valor é cobrado. Ao ligar um meio de pagamento, é ele quem muda o pedido de pendente para confirmado.')}
        </div>

        <div class="cel largo">
          <div class="rotulo-linha">
            <p class="rotulo">Pedidos<small>${pedidos.length}</small></p>
            <form class="filtros" data-form="filtro-pedidos">
              <select name="status" aria-label="Filtrar por situação" data-enviar>
                <option value="">Todos</option>
                <option value="pago" ${estado.pedidos.status === 'pago' ? 'selected' : ''}>Confirmados</option>
                <option value="pendente" ${estado.pedidos.status === 'pendente' ? 'selected' : ''}>Pendentes</option>
                <option value="estornado" ${estado.pedidos.status === 'estornado' ? 'selected' : ''}>Estornados</option>
              </select>
              <input name="busca" type="search" placeholder="Nome, @, código" value="${esc(estado.pedidos.busca)}" aria-label="Buscar pedido">
            </form>
          </div>
          <div class="rolagem alta"><table class="tabela">
            <thead><tr><th>Quando</th><th>Comprador</th><th>Pedido</th><th class="num">Valor</th><th>Situação</th><th></th></tr></thead>
            <tbody>${pedidos.map((p) => `
              <tr class="${p.status}">
                <td class="quando">${fmt.diaHora(p.criado_em)}</td>
                <td>${esc(p.comprador || '—')}<small>${esc(p.instagram || '')}</small></td>
                <td>${p.quantidade} × ${esc(p.lote)}<small>${p.promoter ? `via ${esc(p.promoter)}, código ${esc(p.codigo_promoter)}` : 'compra direta'}</small></td>
                <td class="num">${fmt.brl(p.valor_total)}<small>${METODO[p.metodo] || ''}</small></td>
                <td>${marca(p.status, p.status === 'pago' ? 'Confirmado' : p.status === 'pendente' ? 'Pendente' : 'Estornado')}</td>
                <td class="acoes">
                  ${p.status === 'pendente' ? `<button class="elo" data-acao="pedido-status" data-id="${p.id}" data-status="pago">Confirmar</button>` : ''}
                  ${p.codigos ? `<button class="elo" data-acao="ver-ingressos" data-codigos="${esc(p.codigos)}" data-nome="${esc(p.comprador || '')}">Ingressos</button>` : ''}
                  ${p.status !== 'estornado' ? `<button class="elo suave" data-acao="pedido-status" data-id="${p.id}" data-status="estornado">Estornar</button>` : ''}
                </td>
              </tr>`).join('') || '<tr><td colspan="6" class="vazio">Nenhum pedido com esse filtro. Limpe a busca ou registre uma venda ao lado.</td></tr>'}
            </tbody>
          </table></div>
        </div>

        <div class="cel">
          <p class="rotulo">Aparência do ingresso</p>
          <form class="form-coluna" data-form="design" id="form-design">
            <label>Frase<input name="frase" maxlength="120" value="${esc(CFG.ingresso_design.frase || '')}"></label>
            <label>Rodapé<input name="rodape" maxlength="120" value="${esc(CFG.ingresso_design.rodape || '')}"></label>
            <label>Clima<select name="clima">
              ${[['nevoa', 'Névoa verde'], ['espelho', 'Espelho'], ['noite', 'Noite']].map(([k, v]) => `<option value="${k}" ${CFG.ingresso_design.clima === k ? 'selected' : ''}>${v}</option>`).join('')}
            </select></label>
            <div class="caixas">
              ${[['mostrar_nome', 'Nome do titular'], ['mostrar_lote', 'Lote'], ['mostrar_local', 'Local']].map(([k, v]) =>
                `<label class="caixa"><input type="checkbox" name="${k}" ${CFG.ingresso_design[k] ? 'checked' : ''}><span>${v}</span></label>`).join('')}
            </div>
            <button class="botao">Salvar aparência</button>
          </form>
        </div>
        <div class="cel cel-previa">
          <p class="rotulo">Prévia</p>
          <div id="previa-ingresso" data-codigo="${esc(amostra || '')}"><p class="vazio">${amostra ? 'Carregando...' : 'A prévia aparece com a primeira venda confirmada.'}</p></div>
          ${amostra ? `<a class="elo" href="/ingresso/${esc(amostra)}" target="_blank" rel="noopener">Abrir como o convidado vê</a>` : ''}
        </div>
        <div class="cel">
          <p class="rotulo">Portaria</p>
          <p class="numero">${entrada.dentro}<small> de ${entrada.emitidos} dentro</small></p>
          <form class="form-coluna com-folga" data-form="checkin">
            <label>Código do ingresso<input name="codigo" placeholder="AV-XXXX-XXXX" autocomplete="off" required></label>
            <button class="botao">Liberar entrada</button>
          </form>
          <p id="checkin-resultado" class="resultado" aria-live="polite"></p>
          ${entrada.ultimos.length ? `<ul class="agenda">${entrada.ultimos.map((u) => `<li><time>${fmt.hora(u.checkin_em)}</time><span>${esc(u.titular)}</span><small>${esc(u.lote)}</small></li>`).join('')}</ul>` : ''}
          ${nota('Um leitor de QR comum funciona como teclado: aponte para o ingresso e o código cai neste campo.')}
        </div>
      </section>`);

    if (amostra) desenharPrevia(amostra);
  }

  let previaCache = {};
  async function desenharPrevia(codigo) {
    const alvo = $('#previa-ingresso');
    if (!alvo) return;
    try {
      if (!previaCache[codigo]) {
        const [ing, qr] = await Promise.all([api(`/api/ingressos/${codigo}`), api(`/api/ingressos/${codigo}/qr`).catch(() => ({ linhas: [] }))]);
        previaCache = { [codigo]: { ing, qr } };
      }
      const { ing, qr } = previaCache[codigo];
      const f = $('#form-design');
      const design = f ? {
        frase: f.frase.value, rodape: f.rodape.value, clima: f.clima.value,
        mostrar_nome: f.mostrar_nome.checked, mostrar_lote: f.mostrar_lote.checked, mostrar_local: f.mostrar_local.checked,
      } : null;
      alvo.innerHTML = ingresso(ing, qr.linhas, design);
    } catch (e) {
      alvo.innerHTML = `<p class="vazio">${esc(e.message)}</p>`;
    }
  }

  // ------------------------------------------------------------ 3. promoters

  async function promoters() {
    const d = await api('/api/promoters');
    const { promoters: ps, faixas, totais } = d;
    const maxV = Math.max(1, ...ps.map((p) => p.vendas));
    palco(`
      ${cabeca('Promoters', 'Cada promoter tem um código e um link. Toda venda com o código entra na conta dele, e a comissão sai da faixa que ele alcançou.')}

      <section class="quadro q-quatro">
        <div class="cel cel-num"><p class="rotulo">Ingressos por código</p><p class="numero">${totais.vendas}</p><p class="apoio">${ps.filter((p) => p.ativo).length} promoters ligados</p></div>
        <div class="cel cel-num"><p class="rotulo">Receita por código</p><p class="numero">${fmt.brl(totais.receita)}</p></div>
        <div class="cel cel-num"><p class="rotulo">Comissão a pagar</p><p class="numero">${fmt.brl(totais.comissao)}</p></div>
        <div class="cel cel-num"><p class="rotulo">Sem movimento</p><p class="numero">${totais.parados}</p><p class="apoio">5 dias ou mais sem vender</p></div>

        <div class="cel total">
          <p class="rotulo">Desempenho</p>
          <div class="rolagem"><table class="tabela">
            <thead><tr><th class="num">#</th><th>Promoter</th><th>Código</th><th>Vendas</th><th class="num">Receita</th><th>Faixa</th><th class="num">Comissão</th><th class="num">Stories</th><th>Situação</th><th></th></tr></thead>
            <tbody>${ps.map((p) => `
              <tr class="${p.ativo ? '' : 'desligado'}">
                <td class="num">${p.posicao}</td>
                <td>${esc(p.nome)}<small>${esc(p.instagram || '')}</small></td>
                <td><code>${esc(p.codigo)}</code></td>
                <td><span class="mini-barra" data-dica="${pl(p.vendas, 'ingresso', 'ingressos')}"><i style="width:${(p.vendas / maxV) * 100}%"></i></span><b class="mini-valor">${p.vendas}</b></td>
                <td class="num">${fmt.brl(p.receita)}</td>
                <td>${p.faixa ? `${fmt.n(p.faixa.percentual)}%` : '—'}${p.proxima_faixa ? `<small>${p.faltam === 1 ? 'falta 1' : `faltam ${p.faltam}`} para ${fmt.n(p.proxima_faixa.percentual)}%</small>` : '<small>faixa máxima</small>'}</td>
                <td class="num">${fmt.brl(p.comissao)}</td>
                <td class="num">${p.stories}<small>${p.dias_sem_story == null ? 'nenhum' : p.dias_sem_story === 0 ? 'hoje' : `há ${p.dias_sem_story} d`}</small></td>
                <td>${marca(p.situacao === 'parado' ? 'parado' : p.situacao === 'desligado' ? 'estornado' : 'pago', p.situacao)}${p.dias_sem_venda != null && p.ativo ? `<small>última venda há ${p.dias_sem_venda} d</small>` : ''}</td>
                <td class="acoes">
                  <button class="elo" data-acao="copiar" data-texto="${esc(d.base_url)}/convite?ref=${esc(p.codigo)}">Copiar link</button>
                  <a class="elo" href="/p/${esc(p.codigo)}" target="_blank" rel="noopener">Visão dele</a>
                  <button class="elo" data-acao="promoter-story" data-id="${p.id}">+ story</button>
                  <button class="elo suave" data-acao="promoter-ativo" data-id="${p.id}" data-ativo="${p.ativo ? 0 : 1}">${p.ativo ? 'Desligar' : 'Religar'}</button>
                </td>
              </tr>`).join('') || '<tr><td colspan="10" class="vazio">Nenhum promoter ainda. Cadastre o primeiro ao lado.</td></tr>'}
            </tbody>
          </table></div>
          ${nota('“Visão dele” é a página que o promoter abre no celular: vendas, comissão, posição e o link para divulgar. Ele não vê nome de comprador nem dado de outro promoter.')}
        </div>

        <div class="cel meio">
          <p class="rotulo">Trazer um promoter</p>
          <form class="form-coluna" data-form="promoter">
            <label>Nome<input name="nome" required autocomplete="off"></label>
            <label>Instagram<input name="instagram" placeholder="@" autocomplete="off"></label>
            <label>Código<input name="codigo" placeholder="em branco, o painel cria" maxlength="12" autocomplete="off"></label>
            <button class="botao">Cadastrar e gerar link</button>
          </form>
          ${nota('Na 1.0 houve um promoter de teste: ganhou o ingresso + 1 e R$ 100 de consumação para postar no dia. Agora o combinado vira regra escrita.')}
        </div>

        <div class="cel meio">
          <p class="rotulo">Regra de comissão</p>
          <div class="rolagem"><table class="tabela" id="faixas">
            <thead><tr><th class="num">A partir de (vendas)</th><th class="num">% da receita</th><th class="num">Bônus (R$)</th><th>Mimo</th><th></th></tr></thead>
            <tbody>${faixas.map((f) => linhaFaixa(f)).join('')}</tbody>
          </table></div>
          <div class="form-acoes">
            <button class="elo" data-acao="faixa-add">Nova faixa</button>
            <button class="botao" data-acao="faixas-salvar">Salvar regra</button>
          </div>
          ${nota('Comissão = receita paga com o código × percentual da faixa alcançada + bônus. Pedido pendente ou estornado não conta.')}
        </div>
      </section>`);
  }

  const linhaFaixa = (f = {}) => `
    <tr>
      <td class="num"><input class="em-linha num" type="number" min="0" name="min_vendas" value="${f.min_vendas ?? ''}" aria-label="Vendas mínimas"></td>
      <td class="num"><input class="em-linha num" type="number" min="0" max="100" step="0.5" name="percentual" value="${f.percentual ?? ''}" aria-label="Percentual"></td>
      <td class="num"><input class="em-linha num" type="number" min="0" step="10" name="bonus" value="${f.bonus ?? 0}" aria-label="Bônus"></td>
      <td><input class="em-linha" name="mimo" value="${esc(f.mimo || '')}" placeholder="ingresso, consumação..." aria-label="Mimo"></td>
      <td class="acoes"><button class="elo suave" data-acao="faixa-rem">Tirar</button></td>
    </tr>`;

  // ------------------------------------------------------------ 4. automacao

  function linhaDoTempo(autos, ed, agora) {
    const ini = new Date(ed.abertura_vendas + 'T00:00');
    const fim = new Date(ed.data + 'T00:00');
    fim.setDate(fim.getDate() + 2);
    ini.setDate(ini.getDate() - 1);
    const pos = (iso) => Math.max(0, Math.min(100, ((new Date(iso) - ini) / (fim - ini)) * 100));
    const faixas = { post: 0, mensagem: 1, tarefa: 2 };
    const marcos = autos.filter((a) => a.agendado_para).map((a) =>
      `<i class="marco ${a.status}" style="left:${pos(a.agendado_para)}%; --faixa:${faixas[a.tipo] ?? 0}" data-dica="${esc(`${fmt.diaHora(a.agendado_para)}: ${a.titulo} (${STATUS_AUTO[a.status].toLowerCase()})`)}"></i>`).join('');
    const semanas = [];
    for (let d = new Date(ed.abertura_vendas + 'T00:00'); d < fim; d.setDate(d.getDate() + 7)) {
      semanas.push(`<span class="lt-tick" style="left:${pos(d.toISOString())}%">${fmt.dia(d.toISOString())}</span>`);
    }
    return `
      <div class="linha-tempo">
        <div class="lt-faixas"><span>Posts</span><span>Mensagens</span><span>Tarefas</span></div>
        <div class="lt-pista">
          <i class="lt-trilho" style="--faixa:0"></i><i class="lt-trilho" style="--faixa:1"></i><i class="lt-trilho" style="--faixa:2"></i>
          <span class="lt-agora" style="left:${pos(agora)}%"><em>hoje</em></span>
          <span class="lt-festa" style="left:${pos(ed.data + 'T23:00')}%"><em>festa</em></span>
          ${marcos}
          ${semanas.join('')}
        </div>
      </div>
      <div class="legenda">
        <span><i class="marco-l enviada"></i>Enviada</span><span><i class="marco-l agendada"></i>Agendada</span>
        <span><i class="marco-l rascunho"></i>Rascunho ou pausada</span>
      </div>`;
  }

  async function automacao() {
    const [a, c, t] = await Promise.all([
      api('/api/automacoes'),
      api('/api/contatos?' + new URLSearchParams({ segmento: estado.segmento, busca: estado.buscaContato })),
      api('/api/tarefas'),
    ]);
    const ed = CFG.edicao;
    const grupos = [
      ['Sempre ligadas', a.automacoes.filter((x) => x.gatilho !== 'data')],
      ['Na fila', a.automacoes.filter((x) => x.gatilho === 'data' && ['agendada', 'rascunho', 'pausada'].includes(x.status))],
      ['Já saíram', a.automacoes.filter((x) => x.gatilho === 'data' && x.status === 'enviada')],
    ];
    const linhaAuto = (x) => `
      <tr class="${x.status}">
        <td class="quando">${x.gatilho === 'data' ? `${fmt.diaHora(x.agendado_para)}<small>${dMenos(x.agendado_para, ed.data)}</small>` : x.gatilho === 'compra' ? 'A cada compra' : 'A cada resposta'}</td>
        <td>${esc(x.titulo)}<small>${esc(x.tipo === 'tarefa' ? 'Tarefa' : x.canal || x.tipo)}</small></td>
        <td class="texto">${esc(x.conteudo || '')}${x.checagem && !x.checagem.ok ? `<small class="alerta" data-dica="${esc(x.checagem.alertas.join(' '))}">Tom da marca: ${pl(x.checagem.alertas.length, 'alerta', 'alertas')}</small>` : ''}</td>
        <td>${esc(x.publico || '—')}<small>${x.status === 'enviada' && x.alcance != null ? `${x.alcance} alcançados` : x.alcance_previsto != null ? `${x.alcance_previsto} pessoas hoje` : ''}</small></td>
        <td>${marca(x.status, STATUS_AUTO[x.status])}</td>
        <td class="acoes">
          ${x.status === 'rascunho' || x.status === 'pausada' ? `<button class="elo" data-acao="auto-status" data-id="${x.id}" data-status="${x.gatilho === 'data' ? 'agendada' : 'ativa'}">${x.status === 'rascunho' ? 'Agendar' : 'Retomar'}</button>` : ''}
          ${x.status === 'agendada' || x.status === 'ativa' ? `<button class="elo" data-acao="auto-status" data-id="${x.id}" data-status="pausada">Pausar</button>` : ''}
          <button class="elo suave" data-acao="auto-apagar" data-id="${x.id}">Apagar</button>
        </td>
      </tr>`;
    const colunas = [['a_fazer', 'A fazer'], ['andamento', 'Em andamento'], ['feito', 'Feito']];
    const proximo = { a_fazer: ['andamento', 'Começar'], andamento: ['feito', 'Concluir'], feito: ['a_fazer', 'Reabrir'] };

    palco(`
      ${cabeca('Automação', 'O que sai, para quem e quando. Mensagens, posts e tarefas alinhados à contagem da festa.',
        `<button class="botao ${a.vencidas ? '' : 'fantasma'}" data-acao="auto-executar">Disparar o que venceu${a.vencidas ? ` (${a.vencidas})` : ''}</button>`)}

      <section class="quadro q-dois">
        <div class="cel total">
          <p class="rotulo">Linha do tempo até a festa</p>
          ${linhaDoTempo(a.automacoes, ed, a.agora)}
          ${nota('O disparo aqui é registrado, não enviado: nenhum canal real está ligado ainda. Conectando Instagram, WhatsApp ou e-mail, esta fila passa a sair de verdade.')}
        </div>

        <div class="cel largo">
          ${grupos.filter(([, l]) => l.length).map(([nome, l]) => `
            <p class="rotulo">${nome}<small>${l.length}</small></p>
            <div class="rolagem"><table class="tabela tabela-autos">
              <thead><tr><th>Quando</th><th>O quê</th><th>Texto</th><th>Para quem</th><th>Situação</th><th></th></tr></thead>
              <tbody>${l.map(linhaAuto).join('')}</tbody>
            </table></div>`).join('') || '<p class="vazio">Nenhuma automação criada.</p>'}
        </div>

        <div class="cel">
          <p class="rotulo">Nova automação</p>
          <form class="form-coluna" data-form="automacao" id="form-auto">
            <div class="par">
              <label>Tipo<select name="tipo" data-ao-mudar="auto-tipo"><option value="mensagem">Mensagem</option><option value="post">Post</option><option value="tarefa">Tarefa para a equipe</option></select></label>
              <label>Quando<select name="gatilho" data-ao-mudar="auto-gatilho"><option value="data">Data marcada</option><option value="compra">A cada compra</option><option value="resposta">A cada resposta</option></select></label>
            </div>
            <label>Título<input name="titulo" required autocomplete="off"></label>
            <label data-so="nao-tarefa">Canal<input name="canal" list="canais" placeholder="WhatsApp, stories do Instagram..." autocomplete="off"></label>
            <datalist id="canais"><option>WhatsApp</option><option>Direct do Instagram</option><option>Stories do Instagram</option><option>Feed do Instagram</option><option>Reels do Instagram</option><option>TikTok</option><option>E-mail</option></datalist>
            <label data-so="nao-tarefa">Texto<textarea name="conteudo" rows="4" data-checar></textarea></label>
            <div id="checagem-auto" class="checagem" aria-live="polite"></div>
            <label data-so="nao-tarefa">Para quem<select name="publico">${CFG.publicos.map((p) => `<option>${esc(p)}</option>`).join('')}</select></label>
            <label data-so="tarefa" hidden>Responsável<select name="responsavel">${CFG.equipe.map((p) => `<option>${esc(p.nome)}</option>`).join('')}</select></label>
            <label data-so="data">Data e hora<input name="agendado_para" type="datetime-local" value="${a.agora.slice(0, 11)}19:00"></label>
            <button class="botao">Criar automação</button>
          </form>
        </div>

        <div class="cel total">
          <div class="rotulo-linha">
            <p class="rotulo">Pessoas<small>${c.contatos.length}</small></p>
            <form class="filtros" data-form="filtro-contatos">
              <input name="busca" type="search" placeholder="Nome, @, cidade, etiqueta" value="${esc(estado.buscaContato)}" aria-label="Buscar pessoa">
            </form>
          </div>
          <div class="fichas">${Object.entries(c.segmentos).map(([s, n]) =>
            `<button class="ficha ${s === estado.segmento ? 'ativa' : ''}" data-acao="segmento" data-seg="${esc(s)}">${esc(s)}<b>${n}</b></button>`).join('')}</div>
          <div class="rolagem alta"><table class="tabela">
            <thead><tr><th>Nome</th><th>Cidade</th><th>Faixa</th><th>Quer ouvir</th><th>Bebe</th><th>Chegou por</th><th class="num">Ingressos</th><th class="num">Gasto</th><th>Anotações</th><th></th></tr></thead>
            <tbody>${c.contatos.map((p) => `
              <tr>
                <td>${esc(p.nome)}${p.veterano ? ' <span class="selo" data-dica="Esteve na 1.0">1.0</span>' : ''}<small>${esc(p.instagram || '')}</small></td>
                <td>${esc(p.cidade || '—')}<small>${esc(p.bairro || '')}</small></td>
                <td>${esc(p.faixa_etaria || '—')}</td>
                <td>${esc(p.genero_favorito || '—')}</td>
                <td>${esc(p.bebida || '—')}</td>
                <td>${esc(p.origem || '—')}</td>
                <td class="num">${p.ingressos}</td>
                <td class="num">${fmt.brl(p.gasto)}</td>
                <td class="texto">${esc(p.tags || '')}${p.notas ? `<small>${esc(p.notas)}</small>` : ''}</td>
                <td class="acoes"><button class="elo" data-acao="contato-editar" data-id="${p.id}" data-nome="${esc(p.nome)}" data-tags="${esc(p.tags || '')}" data-notas="${esc(p.notas || '')}">Anotar</button></td>
              </tr>`).join('') || '<tr><td colspan="10" class="vazio">Ninguém neste recorte.</td></tr>'}
            </tbody>
          </table></div>
          ${nota('Cada recorte acima é um público que a central pode usar em “Para quem”. Gosto musical e bebida vêm da pergunta feita na hora da compra.')}
        </div>

        <div class="cel total">
          <p class="rotulo">Tarefas da equipe</p>
          <div class="colunas-tarefa">${colunas.map(([k, nome]) => `
            <div>
              <p class="col-titulo">${nome} <b>${t.tarefas.filter((x) => x.status === k).length}</b></p>
              <ul class="tarefas">${t.tarefas.filter((x) => x.status === k).map((x) => `
                <li class="${x.status !== 'feito' && x.prazo && x.prazo < t.hoje ? 'vencida' : ''} p-${x.prioridade}">
                  <p>${esc(x.titulo)}</p>
                  <small>${esc(x.responsavel || 'Sem dono')}, ${x.prazo ? 'até ' + fmt.dia(x.prazo) : 'sem prazo'}.${x.origem === 'automatica' ? ' Criada pelo painel.' : ''}${x.prioridade === 'alta' ? ' Prioridade alta.' : ''}</small>
                  <span class="acoes">
                    <button class="elo" data-acao="tarefa-status" data-id="${x.id}" data-status="${proximo[k][0]}">${proximo[k][1]}</button>
                    <button class="elo suave" data-acao="tarefa-apagar" data-id="${x.id}">Apagar</button>
                  </span>
                </li>`).join('') || '<li class="vazio">Vazio.</li>'}
              </ul>
            </div>`).join('')}
          </div>
          <form class="form-linha" data-form="tarefa">
            <label>Nova tarefa<input name="titulo" required autocomplete="off"></label>
            <label>Responsável<select name="responsavel">${t.equipe.map((p) => `<option>${esc(p.nome)}</option>`).join('')}</select></label>
            <label>Prazo<input name="prazo" type="date" value="${t.hoje}"></label>
            <label>Prioridade<select name="prioridade"><option value="media">Média</option><option value="alta">Alta</option><option value="baixa">Baixa</option></select></label>
            <button class="botao">Criar tarefa</button>
          </form>
          ${nota('O painel também delega sozinho: lote a 80% gera “preparar virada”, lote esgotado gera “anunciar virada”, e cada ponto cego em Visões pode virar tarefa com um toque.')}
        </div>
      </section>`);
  }

  // ------------------------------------------------------------ 5. visoes

  const botoesAcao = (acoes) => (acoes && acoes.length
    ? `<button class="botao" data-acao="executar" data-acoes="${esc(JSON.stringify(acoes))}">${esc(acoes[0].rotulo)}</button>` : '');

  async function visoes() {
    const v = await api('/api/visoes');
    const m = v.metricas, pb = v.publico;
    const bloco = (titulo, lista) => (lista.length ? `<div><p class="col-titulo">${titulo}</p>${barras(lista)}</div>` : '');
    palco(`
      ${cabeca('Visões', 'O que os números dizem e o que fazer com isso. Três leituras: preço, público e pontos cegos. Cada uma mostra a conta que fez.')}

      <section class="quadro q-dois">
        <div class="cel total cel-sintese">
          <p class="sintese">${m.vendidos
            ? `${m.vendidos} de ${m.capacidade} vendidos. O ritmo está em ${m.indice != null ? fmt.n(m.indice, 2) + '×' : '—'} do necessário para lotar e a projeção fecha em ${m.projecao.central}. A bilheteria já cobre ${m.cobertura_custo}% do custo da 1.0.`
            : 'Ainda sem vendas nesta edição. As leituras abaixo partem do histórico da 1.0.'}</p>
        </div>

        <div class="cel largo">
          <p class="rotulo">Leitura de preço</p>
          <ul class="leituras">${v.precos.map((p) => `
            <li class="tom-${p.tom}">
              <span class="tom-rotulo">${TOM[p.tom] || ''}</span>
              <h3>${esc(p.titulo)}</h3>
              <p>${esc(p.leitura)}</p>
              <p class="sugestao">${esc(p.sugestao)}</p>
              ${p.impacto ? `<p class="impacto">${p.impacto > 0 ? '+' : ''}${fmt.brl(p.impacto)} se o lote esgotar</p>` : ''}
              <div class="leitura-pe">${botoesAcao(p.acoes)}<details><summary>Como li isso</summary><p>${esc(p.como_li)}</p></details></div>
            </li>`).join('')}</ul>
        </div>

        <div class="cel">
          <p class="rotulo">Premissas</p>
          <ul class="premissas">${v.premissas.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>
          ${nota('Toda projeção é uma aposta com regras. Se a última semana da sua cidade vende mais (ou menos) que 1,8×, o número muda junto.')}
        </div>

        <div class="cel total">
          <p class="rotulo">Leitura do público<small>${pb.total} compradores</small></p>
          ${pb.total ? `
          <div class="publico-topo">
            <p class="numero">${pb.veteranos}%<small> já estiveram na 1.0</small></p>
            <p class="numero">${pb.em_grupo}%<small> compram 2 ou mais</small></p>
            <div class="noite">
              <p class="col-titulo">A noite que a casa pede, das 23h às 5h</p>
              <div class="noite-barra">${pb.noite.map((b) => {
                const dur = Number.isInteger(b.horas) ? `${b.horas}h` : `${Math.floor(b.horas) ? Math.floor(b.horas) + 'h' : ''}30`;
                return `<span style="flex:${b.horas}" data-dica="${esc(b.genero)}, ${dur}">${esc(b.genero)}<b>${dur}</b></span>`;
              }).join('')}</div>
            </div>
          </div>
          <div class="publico-grade">
            ${bloco('Quer ouvir', pb.generos)}
            ${bloco('Bebe', pb.bebidas)}
            ${bloco('Faixa de idade', pb.faixas)}
            ${bloco('Chegou por', pb.origens)}
            ${bloco('De onde vem', pb.cidades)}
            <div><p class="col-titulo">Hora da compra</p>${horas(pb.horas)}</div>
          </div>
          <ul class="recomendacoes">${pb.recomendacoes.map((r) => `<li><span class="frente">${esc(r.frente)}</span><h3>${esc(r.titulo)}</h3><p>${esc(r.texto)}</p></li>`).join('')}</ul>`
          : '<p class="vazio">A leitura do público nasce com as primeiras compras: idade, cidade, o que a pessoa quer ouvir e beber.</p>'}
        </div>

        <div class="cel total">
          <p class="rotulo">Pontos cegos<small>${v.riscos.length} riscos encontrados</small></p>
          ${v.riscos.length ? `<ul class="leituras cegos">${v.riscos.map((r) => `
            <li>
              <span class="nivel ${r.nivel}">${NIVEL[r.nivel]}</span>
              <h3>${esc(r.titulo)}</h3>
              <p>${esc(r.leitura)}</p>
              <p class="sugestao">${esc(r.mitigacao)}</p>
              <div class="leitura-pe">${botoesAcao(r.acoes)}${r.feito ? `<span class="marca-st pago">${esc(r.feito)}</span>` : ''}</div>
            </li>`).join('')}</ul>` : '<p class="vazio">Nenhum ponto cego encontrado.</p>'}
        </div>
      </section>`);
  }

  // ------------------------------------------------------------ 6. laboratorio

  async function laboratorio() {
    const r = estado.roteiro;
    const [rk, vt, tx, rt, st] = await Promise.all([
      api('/api/lab/ranking'),
      api('/api/lab/votacao'),
      api('/api/lab/texto', 'POST', { objetivo: estado.objetivo }),
      api('/api/lab/roteiro?' + new URLSearchParams({ lotacao: r.lotacao, energia: r.energia, hora: r.hora, votos: r.votos ? 1 : 0 })),
      api('/api/lab/sentimento'),
    ]);
    const maxV = Math.max(1, ...vt.opcoes.map((o) => o.votos));
    const maxT = Math.max(1, ...st.temas.map((t) => Math.max(t.positivo, t.critico)));
    const horasNoite = ['23:00', '23:30', '00:00', '00:30', '01:00', '01:30', '02:00', '02:30', '03:00', '03:30', '04:00', '04:30'];
    const ideia = (titulo, resumo, corpo) => `
      <article class="ideia">
        <header><h2>${titulo}</h2><p>${resumo}</p></header>
        <div class="ideia-corpo">${corpo}</div>
      </article>`;

    palco(`
      ${cabeca('Laboratório', 'Cinco ideias para a próxima fase do painel, cada uma com um protótipo que já funciona sobre os dados daqui.')}

      ${ideia('O jogo dos promoters', 'Vender vira progressão: pontos, níveis com nome da casa e missões curtas que renovam o fôlego no meio da campanha.', `
        <div class="rolagem"><table class="tabela">
          <thead><tr><th class="num">#</th><th>Promoter</th><th>Nível</th><th class="num">Pontos</th><th>Missões</th><th class="num">Sequência</th></tr></thead>
          <tbody>${rk.ranking.map((p) => `
            <tr>
              <td class="num">${p.posicao}</td>
              <td>${esc(p.nome)}<small>${p.vendas} vendas, ${p.stories} stories</small></td>
              <td>${esc(p.nivel)}${p.proximo_nivel ? `<small>faltam ${p.proximo_nivel.faltam} para ${esc(p.proximo_nivel.nome)}</small>` : '<small>topo</small>'}</td>
              <td class="num"><b>${p.pontos}</b></td>
              <td><div class="missoes">${p.missoes.map((ms) => `
                <span class="missao ${ms.feito >= ms.alvo ? 'feita' : ''}" data-dica="${esc(ms.regra)}. Vale ${ms.pontos} pontos.">
                  ${esc(ms.nome)} <b>${ms.feito}/${ms.alvo}</b><i style="width:${Math.min(100, (ms.feito / ms.alvo) * 100)}%"></i>
                </span>`).join('')}</div></td>
              <td class="num">${p.sequencia} d</td>
            </tr>`).join('') || '<tr><td colspan="6" class="vazio">Sem promoters ligados.</td></tr>'}
          </tbody>
        </table></div>
        ${nota(esc(rk.regras) + ' Níveis: ' + rk.niveis.map((n) => `${esc(n.nome)} (${n.a_partir_de})`).join(', ') + '.')}`)}

      ${ideia('A pista decide', 'Durante a festa, quem está dentro vota no rumo do próximo bloco. Só entram gêneros da curadoria: a pista escolhe o caminho, não o destino.', `
        <div class="voto-grade">
          <div>
            <p class="col-titulo">${esc(vt.pergunta)} <b>${vt.total} votos</b></p>
            <div class="barras votos">${vt.opcoes.map((o) => `
              <div class="barra-linha" data-dica="${esc(o.opcao)}: ${pl(o.votos, 'voto', 'votos')}">
                <span class="barra-rotulo">${esc(o.opcao)}</span>
                <span class="barra-trilho"><i style="width:${(o.votos / maxV) * 100}%"></i></span>
                <span class="barra-valor">${o.pct}%</span>
                <button class="elo" data-acao="votar" data-opcao="${esc(o.opcao)}">Votar</button>
              </div>`).join('')}</div>
          </div>
          <div>
            <p class="col-titulo">No celular de quem está na festa</p>
            <p class="apoio">O convidado abre a página pelo QR da pulseira ou do cardápio e vota uma vez por bloco.</p>
            <a class="botao fantasma" href="/pista" target="_blank" rel="noopener">Abrir a página da pista</a>
            <button class="elo suave" data-acao="votos-zerar">Zerar a rodada</button>
          </div>
        </div>`)}

      ${ideia('Estúdio de texto', 'Legendas e mensagens no tom da casa, sempre em três níveis de mistério, com uma checagem que barra o que soa como festa comum.', `
        <div class="texto-grade">
          <div>
            <label class="solto">Para quê<select data-ao-mudar="objetivo">${Object.entries(CFG.objetivos).map(([k, v]) => `<option value="${k}" ${k === estado.objetivo ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></label>
            <ul class="versoes">${tx.versoes.map((x) => `
              <li>
                <span class="frente">${esc(x.nivel)}</span>
                <p class="versao">${esc(x.texto)}</p>
                <div class="acoes"><button class="elo" data-acao="copiar" data-texto="${esc(x.texto)}">Copiar</button>
                <button class="elo" data-acao="texto-agendar" data-texto="${esc(x.texto)}" data-titulo="${esc(tx.rotulo)}">Levar para a central</button></div>
              </li>`).join('')}</ul>
          </div>
          <div>
            <label class="solto">Checar um texto seu<textarea rows="5" id="texto-livre" data-checar="livre" placeholder="Cole aqui uma legenda ou mensagem"></textarea></label>
            <div id="checagem-livre" class="checagem" aria-live="polite"></div>
          </div>
        </div>`)}

      ${ideia('Roteiro vivo', 'O roteiro da noite deixa de ser fixo. Lotação, energia da pista e o voto do público reordenam os blocos e avisam a operação.', `
        <div class="roteiro-grade">
          <form class="form-coluna" data-form="roteiro">
            <label>Hora<select name="hora" data-enviar>${horasNoite.map((h) => `<option ${h === r.hora ? 'selected' : ''}>${h}</option>`).join('')}</select></label>
            <label>Casa cheia em <output>${r.lotacao}%</output><input type="range" name="lotacao" min="0" max="100" step="5" value="${r.lotacao}" data-enviar></label>
            <label>Energia da pista <output>${r.energia} de 5</output><input type="range" name="energia" min="1" max="5" value="${r.energia}" data-enviar></label>
            <label class="caixa"><input type="checkbox" name="votos" ${r.votos ? 'checked' : ''} data-enviar><span>Ouvir o voto da pista${vt.lider ? ` (${esc(vt.lider)} na frente)` : ''}</span></label>
          </form>
          <div>
            <ol class="blocos">${rt.blocos.map((b) => `
              <li class="${b.agora ? 'agora' : ''} ${b.mudou ? 'mudou' : ''}">
                <time>${b.hora}</time><span>${esc(b.genero)}</span><small>${esc(b.fase)}${b.mudou ? ', ajustado' : ''}${b.agora ? ', tocando agora' : ''}</small>
              </li>`).join('')}</ol>
            <ul class="ajustes">${rt.ajustes.map((a) => `<li>${esc(a)}</li>`).join('')}${rt.avisos.map((a) => `<li class="aviso-op">${esc(a)}</li>`).join('')}</ul>
          </div>
        </div>`)}

      ${ideia('Leitura pós-evento', `Os comentários do dia seguinte viram mapa: o que repetir e o que corrigir, por tema. Aqui, sobre a ${esc(st.edicao)}.`, `
        <div class="pos-grade">
          <div>
            <p class="numero">${st.positivos_pct}%<small> de comentários positivos${st.nota_media ? `, nota média ${fmt.n(st.nota_media, 1)}` : ''}</small></p>
            <div class="divergente">
              <div class="div-cab"><span>Críticas</span><span>Tema</span><span>Elogios</span></div>
              ${st.temas.map((t) => `
              <div class="div-linha" data-dica="${esc(t.tema)}: ${pl(t.positivo, 'elogio', 'elogios')}, ${pl(t.critico, 'crítica', 'críticas')}">
                <span class="div-neg"><b>${t.critico || ''}</b><i style="width:${(t.critico / maxT) * 100}%"></i></span>
                <span class="div-tema">${esc(t.tema)}</span>
                <span class="div-pos"><i style="width:${(t.positivo / maxT) * 100}%"></i><b>${t.positivo || ''}</b></span>
              </div>`).join('')}
            </div>
            <div class="par conclusoes">
              <div><p class="col-titulo">Repetir</p><p>${st.repetir.map(esc).join(', ') || '—'}</p></div>
              <div><p class="col-titulo">Corrigir</p><p>${st.corrigir.map(esc).join(', ') || '—'}</p></div>
            </div>
          </div>
          <div>
            <form class="form-coluna" data-form="feedback">
              <label>Acrescentar um comentário<textarea name="texto" rows="3" required placeholder="Uma frase sobre a noite"></textarea></label>
              <button class="botao fantasma">Ler este comentário</button>
            </form>
            <ul class="comentarios">${st.comentarios.slice(0, 5).map((c) => `
              <li><span class="marca-st ${c.tom === 'positivo' ? 'pago' : c.tom === 'neutro' ? 'rascunho' : 'parado'}">${esc(c.tom === 'critico' ? 'crítico' : c.tom)}</span>
              <p>${esc(c.texto)}</p><small>${c.temas.map(esc).join(', ')}</small></li>`).join('')}</ul>
            ${CFG.modo === 'ensaio' ? nota('Os comentários de partida são simulados, escritos em cima do que a 1.0 realmente ensinou: decoração forte, bar e banheiros a corrigir.') : ''}
          </div>
        </div>`)}
    `);
  }

  // ------------------------------------------------------------ acoes

  const ACOES = {
    async 'venda-ensaio'() {
      const p = await api('/api/ensaio/venda', 'POST');
      avisar(`${p.comprador} levou ${p.quantidade} × ${p.lote}${p.promoter ? ` via ${p.promoter}` : ''}.`);
      piscar();
    },
    async modo(el) {
      const real = el.dataset.modo === 'real';
      const ok = await confirmar(
        real ? 'Começar do zero?' : 'Voltar ao ensaio?',
        real
          ? 'Os dados simulados são apagados. Ficam só os fatos da marca: a 1.0, a data, o local e a capacidade da próxima edição. O relógio passa a ser o de hoje.'
          : 'Tudo o que foi lançado no modo real é apagado e o painel volta aos dados simulados de 17/04/2027.',
        real ? 'Apagar e começar' : 'Apagar e voltar');
      if (!ok) return false;
      await api('/api/config/modo', 'POST', { modo: el.dataset.modo });
      CFG = await api('/api/config');
      trilhoPe();
      previaCache = {};
      estado.previa = null;
      avisar(real ? 'Painel limpo. Comece criando os lotes.' : 'Ensaio restaurado.');
    },
    async 'lote-apagar'(el) { await api(`/api/lotes/${el.dataset.id}`, 'DELETE'); avisar('Lote apagado.'); },
    async 'pedido-status'(el) {
      if (el.dataset.status === 'estornado' && !(await confirmar('Estornar o pedido?', 'Os ingressos deste pedido são cancelados e voltam para o lote.', 'Estornar'))) return false;
      await api(`/api/pedidos/${el.dataset.id}`, 'PATCH', { status: el.dataset.status });
      avisar(el.dataset.status === 'pago' ? 'Pagamento confirmado. Ingressos emitidos.' : 'Pedido estornado.');
    },
    'ver-ingressos'(el) {
      const codigos = el.dataset.codigos.split(' ').filter(Boolean);
      janela(`
        <h3>Ingressos de ${esc(el.dataset.nome)}</h3>
        <ul class="lista-ingressos">${codigos.map((c) => `
          <li><code>${esc(c)}</code>
            <span class="acoes"><a class="elo" href="/ingresso/${esc(c)}" target="_blank" rel="noopener">Abrir</a>
            <button class="elo" data-acao="previa" data-codigo="${esc(c)}">Usar na prévia</button></span></li>`).join('')}</ul>
        <div class="janela-acoes"><button class="botao fantasma" data-acao="fechar">Fechar</button></div>`);
      return false;
    },
    previa(el) { estado.previa = el.dataset.codigo; $('#janela').close(); },
    fechar() { $('#janela').close(); return false; },
    async copiar(el) {
      try { await navigator.clipboard.writeText(el.dataset.texto); avisar('Copiado.'); } catch (_) { janela(`<h3>Copie daqui</h3><p><code>${esc(el.dataset.texto)}</code></p><div class="janela-acoes"><button class="botao fantasma" data-acao="fechar">Fechar</button></div>`); }
      return false;
    },
    async 'promoter-story'(el) { await api(`/api/promoters/${el.dataset.id}/stories`, 'POST'); avisar('Story registrado.'); },
    async 'promoter-ativo'(el) { await api(`/api/promoters/${el.dataset.id}`, 'PATCH', { ativo: el.dataset.ativo === '1' }); },
    'faixa-add'() { $('#faixas tbody').insertAdjacentHTML('beforeend', linhaFaixa()); return false; },
    'faixa-rem'(el) { el.closest('tr').remove(); return false; },
    async 'faixas-salvar'() {
      const faixas = $$('#faixas tbody tr').map((tr) => Object.fromEntries($$('input', tr).map((i) => [i.name, i.value])));
      await api('/api/comissoes', 'PUT', { faixas });
      avisar('Regra de comissão salva.');
    },
    async 'auto-status'(el) { await api(`/api/automacoes/${el.dataset.id}`, 'PATCH', { status: el.dataset.status }); },
    async 'auto-apagar'(el) { await api(`/api/automacoes/${el.dataset.id}`, 'DELETE'); },
    async 'auto-executar'() {
      const r = await api('/api/automacoes/executar', 'POST');
      avisar(r.disparadas.length ? `${pl(r.disparadas.length, 'disparo registrado', 'disparos registrados')}: ${r.disparadas.map((d) => d.titulo).join('; ')}.` : 'Nada vencido para disparar.');
    },
    segmento(el) { estado.segmento = el.dataset.seg; },
    'contato-editar'(el) {
      janela(`
        <h3>${esc(el.dataset.nome)}</h3>
        <form class="form-coluna" data-form="contato">
          <input type="hidden" name="id" value="${esc(el.dataset.id)}">
          <label>Etiquetas<input name="tags" value="${esc(el.dataset.tags)}" placeholder="amigo da casa, DJ, imprensa"></label>
          <label>Anotação<textarea name="notas" rows="3">${esc(el.dataset.notas)}</textarea></label>
          <div class="janela-acoes"><button type="button" class="botao fantasma" data-acao="fechar">Voltar</button><button class="botao">Salvar</button></div>
        </form>`);
      return false;
    },
    async 'tarefa-status'(el) { await api(`/api/tarefas/${el.dataset.id}`, 'PATCH', { status: el.dataset.status }); },
    async 'tarefa-apagar'(el) { await api(`/api/tarefas/${el.dataset.id}`, 'DELETE'); },
    async executar(el) {
      for (const a of JSON.parse(el.dataset.acoes)) await api(a.url, a.metodo, a.corpo);
      avisar('Feito. A leitura foi recalculada.');
    },
    async votar(el) { await api('/api/lab/votacao', 'POST', { opcao: el.dataset.opcao }); },
    async 'votos-zerar'() { await api('/api/lab/votacao', 'DELETE'); avisar('Rodada zerada.'); },
    'texto-agendar'(el) {
      sessionStorage.setItem('av-rascunho', JSON.stringify({ titulo: el.dataset.titulo, conteudo: el.dataset.texto }));
      location.hash = '#automacao';
      return false;
    },
  };

  const FORMS = {
    async lote(d, f) { await api('/api/lotes', 'POST', d); avisar('Lote criado.'); },
    async venda(d) {
      const p = await api('/api/pedidos', 'POST', d);
      estado.previa = p.ingressos[0]?.codigo || estado.previa;
      await redesenhar();
      if (p.ingressos.length) {
        janela(`
          <h3>Venda registrada</h3>
          <p>${esc(p.comprador)} levou ${p.quantidade} × ${esc(p.lote)}, ${fmt.brl(p.valor_total)}.</p>
          <ul class="lista-ingressos">${p.ingressos.map((i) => `<li><code>${esc(i.codigo)}</code><span>${esc(i.titular)}</span><a class="elo" href="/ingresso/${esc(i.codigo)}" target="_blank" rel="noopener">Abrir ingresso</a></li>`).join('')}</ul>
          <div class="janela-acoes"><button class="botao fantasma" data-acao="fechar">Fechar</button></div>`);
      } else avisar('Pedido registrado como pendente.');
      return false;
    },
    'filtro-pedidos'(d) { estado.pedidos = { status: d.status || '', busca: d.busca || '' }; },
    'filtro-contatos'(d) { estado.buscaContato = d.busca || ''; },
    async design(d, f) {
      const corpo = { frase: d.frase, rodape: d.rodape, clima: d.clima, mostrar_nome: f.mostrar_nome.checked, mostrar_lote: f.mostrar_lote.checked, mostrar_local: f.mostrar_local.checked };
      CFG.ingresso_design = await api('/api/config/ingresso', 'PUT', corpo);
      previaCache = {};
      avisar('Aparência salva. Vale para todos os ingressos.');
    },
    async checkin(d) {
      const alvo = $('#checkin-resultado');
      try {
        const r = await api('/api/checkin', 'POST', d);
        await redesenhar();
        $('#checkin-resultado').textContent = r.mensagem;
        $('#checkin-resultado').className = 'resultado ok';
      } catch (e) {
        alvo.textContent = e.message;
        alvo.className = 'resultado erro';
      }
      return false;
    },
    async promoter(d) {
      const p = await api('/api/promoters', 'POST', d);
      avisar(`${p.nome} entrou com o código ${p.codigo}.`);
    },
    async automacao(d) {
      const tarefa = d.tipo === 'tarefa';
      const gatilho = tarefa ? 'data' : d.gatilho;
      const corpo = { tipo: d.tipo, gatilho, titulo: d.titulo, canal: tarefa ? '' : d.canal, conteudo: tarefa ? '' : d.conteudo, publico: tarefa ? d.responsavel : d.publico };
      if (gatilho === 'data') corpo.agendado_para = d.agendado_para;
      await api('/api/automacoes', 'POST', corpo);
      avisar('Automação criada.');
    },
    async tarefa(d) { await api('/api/tarefas', 'POST', d); },
    async contato(d) {
      await api(`/api/contatos/${d.id}`, 'PATCH', { tags: d.tags, notas: d.notas });
      $('#janela').close();
    },
    roteiro(d, f) { estado.roteiro = { lotacao: +d.lotacao, energia: +d.energia, hora: d.hora, votos: f.votos.checked }; },
    async feedback(d) { await api('/api/lab/sentimento', 'POST', d); avisar('Comentário lido e somado ao mapa.'); },
  };

  // ------------------------------------------------------------ eventos

  document.addEventListener('click', async (e) => {
    const el = e.target.closest('[data-acao]');
    if (!el || !ACOES[el.dataset.acao]) return;
    e.preventDefault();
    try {
      const r = await ACOES[el.dataset.acao](el);
      if (r !== false) await redesenhar();
    } catch (err) { avisar(err.message, true); }
  });

  document.addEventListener('submit', async (e) => {
    const f = e.target.closest('form[data-form]');
    if (!f || !FORMS[f.dataset.form]) return;
    e.preventDefault();
    try {
      const r = await FORMS[f.dataset.form](Object.fromEntries(new FormData(f)), f);
      if (r !== false) await redesenhar();
    } catch (err) { avisar(err.message, true); }
  });

  let espera = null;
  async function checar(texto, alvo) {
    if (!alvo) return;
    if (!texto.trim()) { alvo.innerHTML = ''; return; }
    const r = await api('/api/lab/checagem', 'POST', { texto });
    alvo.innerHTML = `
      <p class="checagem-titulo ${r.ok ? 'ok' : 'erro'}">${r.ok ? 'No tom da casa' : `Fora do tom em ${pl(r.alertas.length, 'ponto', 'pontos')}`}</p>
      ${r.alertas.map((a) => `<p class="ch-alerta">${esc(a)}</p>`).join('')}
      ${r.acertos.map((a) => `<p class="ch-acerto">${esc(a)}</p>`).join('')}`;
  }

  document.addEventListener('input', (e) => {
    const t = e.target;
    if (t.matches('[data-checar]')) {
      clearTimeout(espera);
      espera = setTimeout(() => checar(t.value, $(t.dataset.checar === 'livre' ? '#checagem-livre' : '#checagem-auto')).catch(() => {}), 350);
    }
    if (t.closest('#form-design')) {
      const c = $('#previa-ingresso')?.dataset.codigo;
      if (c) desenharPrevia(c);
    }
    if (t.type === 'range') {
      const o = t.closest('label')?.querySelector('output');
      if (o) o.textContent = t.name === 'lotacao' ? `${t.value}%` : `${t.value} de 5`;
    }
  });

  document.addEventListener('change', async (e) => {
    const t = e.target;
    try {
      if (t.dataset.mudar === 'lote') {
        await api(`/api/lotes/${t.dataset.id}`, 'PATCH', { [t.dataset.campo]: t.value });
        avisar('Lote atualizado.');
        await redesenhar();
      } else if (t.hasAttribute('data-enviar')) {
        t.form.requestSubmit();
      } else if (t.dataset.aoMudar === 'objetivo') {
        estado.objetivo = t.value;
        await redesenhar();
      } else if (t.dataset.aoMudar === 'auto-tipo' || t.dataset.aoMudar === 'auto-gatilho') {
        ajustarFormAuto();
      }
    } catch (err) {
      avisar(err.message, true);
      await redesenhar();
    }
  });

  document.addEventListener('search', (e) => { if (e.target.form?.dataset.form) e.target.form.requestSubmit(); });

  function ajustarFormAuto() {
    const f = $('#form-auto');
    if (!f) return;
    const tarefa = f.tipo.value === 'tarefa';
    if (tarefa) f.gatilho.value = 'data';
    f.gatilho.disabled = tarefa;
    $$('[data-so="nao-tarefa"]', f).forEach((el) => (el.hidden = tarefa));
    $$('[data-so="tarefa"]', f).forEach((el) => (el.hidden = !tarefa));
    $$('[data-so="data"]', f).forEach((el) => (el.hidden = f.gatilho.value !== 'data'));
  }

  // dica flutuante (hover em graficos, marcos e barras)
  const dica = $('#dica');
  document.addEventListener('mouseover', (e) => {
    const el = e.target.closest('[data-dica]');
    if (!el) { dica.classList.remove('visivel'); return; }
    dica.textContent = el.dataset.dica;
    dica.classList.add('visivel');
  });
  document.addEventListener('mousemove', (e) => {
    if (!dica.classList.contains('visivel')) return;
    const w = dica.offsetWidth, h = dica.offsetHeight;
    dica.style.left = Math.min(window.innerWidth - w - 12, Math.max(12, e.clientX + 14)) + 'px';
    dica.style.top = (e.clientY + h + 28 > window.innerHeight ? e.clientY - h - 12 : e.clientY + 18) + 'px';
  });
  document.addEventListener('scroll', () => dica.classList.remove('visivel'), true);

  // ------------------------------------------------------------ rotas

  const VISTAS = { panorama, ingressos, promoters, automacao, visoes, laboratorio };

  async function desenhar() {
    const nome = (location.hash || '#panorama').slice(1);
    const vista = VISTAS[nome] || panorama;
    $$('.trilho-nav a').forEach((a) => a.classList.toggle('ativo', a.hash === '#' + (VISTAS[nome] ? nome : 'panorama')));
    $('#palco').dataset.vista = VISTAS[nome] ? nome : 'panorama';
    try {
      await vista();
    } catch (err) {
      palco(`${cabeca('Sem sinal', 'O painel não conseguiu falar com o servidor.')}<p class="vazio">${esc(err.message)}</p>`);
    }
    if (nome === 'automacao') {
      ajustarFormAuto();
      const r = sessionStorage.getItem('av-rascunho');
      if (r) {
        sessionStorage.removeItem('av-rascunho');
        const { titulo, conteudo } = JSON.parse(r);
        const f = $('#form-auto');
        f.tipo.value = 'post';
        ajustarFormAuto();
        f.titulo.value = titulo;
        f.conteudo.value = conteudo;
        checar(conteudo, $('#checagem-auto')).catch(() => {});
        f.scrollIntoView({ block: 'center' });
      }
    }
  }

  async function redesenhar() {
    const y = window.scrollY;
    await desenhar();
    window.scrollTo(0, y);
  }

  window.addEventListener('hashchange', async () => {
    clearInterval(pulso);
    await desenhar();
    window.scrollTo(0, 0);
    $('#palco').focus({ preventScroll: true });
  });

  (async () => {
    try {
      CFG = await api('/api/config');
      trilhoPe();
      await desenhar();
    } catch (err) {
      palco(`<p class="vazio">${esc(err.message)}</p>`);
    }
  })();
})();
