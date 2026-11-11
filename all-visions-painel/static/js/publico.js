/* ALL VISIONS · paginas publicas: convite (compra em modo conceito), ingresso, visao do promoter e votacao da pista */
(() => {
  'use strict';
  const { esc, fmt, api, olho, ingresso } = window.AV;
  const raiz = document.getElementById('publico');
  const { visao, chave } = raiz.dataset;
  const por = (html) => { raiz.innerHTML = `<div class="pub">${html}</div>`; };
  const topo = `${olho()}<p class="pub-marca">ALL VISIONS</p>`;

  // ------------------------------------------------------------ convite

  async function convite() {
    const c = await api('/api/publico/convite?ref=' + encodeURIComponent(chave));
    if (!c.aberto) {
      por(`${topo}
        <p class="pub-linha">Apenas convidados</p>
        <h1>${c.lote ? 'Ainda não.' : 'Fechado.'}</h1>
        <p class="pub-texto">${c.lote && c.abertura ? `O acesso abre em ${fmt.ponto(c.abertura)}. Quem olha cedo entra primeiro.` : 'Não há acesso aberto neste momento. Fique de olho.'}</p>`);
      return;
    }
    por(`${topo}
      <p class="pub-linha">Apenas convidados</p>
      <h1>Você olhou na hora certa.</h1>
      <p class="pub-texto">${fmt.ponto(c.data)}.${c.por ? ` Convite de ${esc(c.por.replace(/\.$/, ''))}.` : ''}</p>
      <form id="f-convite">
        <div class="pub-preco"><span>${esc(c.lote.nome)}${c.lote.ultimos ? ', últimos ingressos' : ''}</span><b>${fmt.brl(c.lote.preco)}</b></div>
        <div class="form-coluna">
          <label>Seu nome<input name="nome" required autocomplete="name"></label>
          <label>Instagram<input name="instagram" placeholder="@" autocomplete="off"></label>
          <div class="par">
            <label>Ingressos<select name="quantidade"><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
            <label>Idade<select name="faixa_etaria"><option value="">—</option><option>18 a 21</option><option>22 a 25</option><option>26 a 30</option><option>31 ou mais</option></select></label>
          </div>
          <label>O que você quer ouvir<select name="genero_favorito"><option value="">—</option>${c.generos.map((g) => `<option>${esc(g)}</option>`).join('')}</select></label>
          <label>O que você bebe<select name="bebida"><option value="">—</option><option>Gin</option><option>Vodka</option><option>Cerveja</option><option>Whisky</option><option>Tequila</option><option>Sem álcool</option></select></label>
          <button class="botao">Confirmar acesso</button>
          <p class="pub-pe" id="convite-erro" aria-live="polite">Modo conceito: nenhum valor é cobrado nesta etapa.</p>
        </div>
      </form>`);
    document.getElementById('f-convite').addEventListener('submit', async (e) => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      try {
        const r = await api('/api/publico/pedido', 'POST', { ...d, lote_id: c.lote.id, ref: c.ref });
        por(`${topo}
          <p class="pub-linha">Acesso confirmado</p>
          <h1>Você está dentro.</h1>
          <p class="pub-texto">Guarde ${r.ingressos.length > 1 ? 'os ingressos' : 'o ingresso'}. O resto, você vê lá.</p>
          <div class="pub-bloco"><ul class="pub-lista">${r.ingressos.map((cod) => `<li><code>${esc(cod)}</code><a class="elo" href="/ingresso/${esc(cod)}">Abrir ingresso</a></li>`).join('')}</ul></div>`);
      } catch (err) {
        const p = document.getElementById('convite-erro');
        p.textContent = err.message;
        p.style.color = 'var(--barro)';
      }
    });
  }

  // ------------------------------------------------------------ ingresso

  async function verIngresso() {
    const [ing, qr] = await Promise.all([api(`/api/ingressos/${encodeURIComponent(chave)}`), api(`/api/ingressos/${encodeURIComponent(chave)}/qr`).catch(() => ({ linhas: [] }))]);
    por(`${ingresso(ing, qr.linhas)}<p class="pub-pe">Mostre este código na entrada. Ele vale uma vez.</p>`);
    document.title = `Ingresso ${ing.codigo}, ALL VISIONS`;
  }

  // ------------------------------------------------------------ visao do promoter

  async function promoter() {
    const p = await api(`/api/promoters/codigo/${encodeURIComponent(chave)}`);
    const prox = p.proxima_faixa;
    const andamento = prox ? Math.min(100, (p.vendas / prox.min_vendas) * 100) : 100;
    por(`${topo}
      <p class="pub-linha">${esc(p.edicao)}, ${fmt.ponto(p.data)}</p>
      <h1>${esc(p.nome)}</h1>
      <div class="pub-numeros">
        <div><b>${p.vendas}</b><span>vendas</span></div>
        <div><b>${fmt.brl(p.comissao)}</b><span>comissão</span></div>
        <div><b>${p.posicao}º</b><span>de ${p.de}</span></div>
      </div>
      <div class="pub-bloco">
        <p class="rotulo">Sua faixa</p>
        <p>${p.faixa ? `${fmt.n(p.faixa.percentual)}% sobre o que você vende${p.faixa.mimo ? `. ${esc(p.faixa.mimo)}.` : '.'}` : 'Faça a primeira venda para entrar na primeira faixa.'}</p>
        <div class="pub-progresso"><i style="width:${andamento}%"></i></div>
        <p class="pub-pe">${prox ? `${p.faltam === 1 ? 'Falta 1 venda' : `Faltam ${p.faltam} vendas`} para ${fmt.n(prox.percentual)}%.${prox.mimo ? ` A próxima faixa traz: ${esc(prox.mimo)}.` : ''}` : 'Você está na faixa mais alta.'}</p>
      </div>
      <div class="pub-bloco">
        <p class="rotulo">Seu link</p>
        <p><code>${esc(p.link)}</code></p>
        <button class="botao fantasma" id="copiar" style="margin-top:14px">Copiar link</button>
        <p class="pub-pe" style="margin-top:10px">Toda compra feita por ele conta para você. Código: <code>${esc(p.codigo)}</code></p>
      </div>
      ${p.jogo ? `<div class="pub-bloco">
        <p class="rotulo">Nível ${esc(p.jogo.nivel)}<small>${p.jogo.pontos} pontos</small></p>
        <ul class="pub-lista">${p.jogo.missoes.map((m) => `<li><span>${esc(m.nome)}<br><small class="pub-pe">${esc(m.regra)}</small></span><b>${m.feito}/${m.alvo}</b></li>`).join('')}</ul>
      </div>` : ''}
      <div class="pub-bloco">
        <p class="rotulo">Últimas vendas</p>
        ${p.ultimas.length ? `<ul class="pub-lista">${p.ultimas.map((v) => `<li><span>${fmt.dia(v.dia)}</span><span>${v.quantidade} × ${esc(v.lote)}</span></li>`).join('')}</ul>` : '<p class="pub-pe">Nenhuma ainda. O primeiro story costuma trazer a primeira.</p>'}
      </div>`);
    document.getElementById('copiar').addEventListener('click', async (e) => {
      try { await navigator.clipboard.writeText(p.link); e.target.textContent = 'Copiado'; } catch (_) { e.target.textContent = 'Selecione e copie acima'; }
    });
  }

  // ------------------------------------------------------------ a pista decide

  async function pista() {
    let meu = sessionStorage.getItem('av-voto');
    const desenhar = (v) => {
      por(`${topo}
        <p class="pub-linha">A pista decide</p>
        <h1>${esc(v.pergunta)}</h1>
        <div class="pub-votos">${v.opcoes.map((o) => `
          <button class="pub-voto ${o.opcao === meu ? 'meu' : ''}" data-opcao="${esc(o.opcao)}" ${meu ? 'disabled' : ''}>
            <i style="width:${meu ? o.pct : 0}%"></i><span>${esc(o.opcao)}</span>${meu ? `<b>${o.pct}%</b>` : ''}
          </button>`).join('')}</div>
        <p class="pub-pe">${meu ? `Seu olhar foi contado. ${v.total} votos nesta rodada.` : 'Um voto por rodada. O resultado aparece depois que você escolhe.'}</p>`);
    };
    desenhar(await api('/api/lab/votacao'));
    raiz.addEventListener('click', async (e) => {
      const b = e.target.closest('.pub-voto');
      if (!b || meu) return;
      meu = b.dataset.opcao;
      sessionStorage.setItem('av-voto', meu);
      desenhar(await api('/api/lab/votacao', 'POST', { opcao: meu }));
    });
    setInterval(async () => { if (meu && !document.hidden) desenhar(await api('/api/lab/votacao')); }, 4000);
  }

  const visoes = { convite, ingresso: verIngresso, promoter, pista };
  (visoes[visao] || convite)().catch((err) => {
    por(`${topo}<p class="pub-linha">Apenas convidados</p><h1>Nada por aqui.</h1><p class="pub-texto">${esc(err.message)}</p>`);
  });
})();
