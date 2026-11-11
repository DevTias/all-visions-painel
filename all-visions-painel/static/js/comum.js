/* ALL VISIONS · utilitarios compartilhados entre o painel e as paginas publicas */
window.AV = (() => {
  'use strict';

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const fmt = {
    brl(v) {
      const n = Number(v || 0);
      const casas = Number.isInteger(n) ? 0 : 2;
      return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
    },
    n(v, casas = 0) {
      return Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
    },
    dia(iso) {
      if (!iso) return '—';
      const [, m, d] = iso.slice(0, 10).split('-');
      return `${d}/${m}`;
    },
    ponto(iso) {
      if (!iso) return '—';
      const [a, m, d] = iso.slice(0, 10).split('-');
      return `${d}.${m}.${a}`;
    },
    hora(iso) {
      return iso && iso.length > 11 ? iso.slice(11, 16) : '';
    },
    diaHora(iso) {
      return iso ? `${fmt.dia(iso)}, ${fmt.hora(iso)}` : '—';
    },
    extenso(iso) {
      if (!iso) return '';
      return new Date(iso.slice(0, 10) + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    },
  };

  async function api(url, metodo = 'GET', corpo) {
    const r = await fetch(url, {
      method: metodo,
      headers: corpo ? { 'Content-Type': 'application/json' } : undefined,
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      const e = new Error(j.erro || j.mensagem || 'Algo não saiu como esperado.');
      e.dados = j;
      throw e;
    }
    return j;
  }

  const olho = (classe = '') => `
    <svg class="olho ${classe}" viewBox="0 0 64 36" aria-hidden="true">
      <path class="olho-contorno" d="M2 18C14 3 50 3 62 18C50 33 14 33 2 18Z"/>
      <circle class="olho-iris" cx="32" cy="18" r="9.5"/>
      <circle class="olho-pupila" cx="32" cy="18" r="3.2"/>
    </svg>`;

  function qrSvg(linhas) {
    if (!linhas || !linhas.length) return '';
    const n = linhas.length;
    let d = '';
    linhas.forEach((linha, y) => {
      for (let x = 0; x < n; x++) if (linha[x] === '1') d += `M${x} ${y}h1v1h-1z`;
    });
    return `<svg class="qr" viewBox="-2 -2 ${n + 4} ${n + 4}" shape-rendering="crispEdges" role="img" aria-label="Código de entrada"><path d="${d}"/></svg>`;
  }

  /* e-ticket. ing = resposta de /api/ingressos/<codigo>; design opcional sobrepoe o salvo */
  function ingresso(ing, linhasQr, design) {
    const ds = Object.assign({ frase: '', rodape: '', clima: 'nevoa', mostrar_nome: true, mostrar_lote: true, mostrar_local: false }, ing.design || {}, design || {});
    const selo = ing.status === 'usado' ? `<p class="ing-selo">Entrada registrada às ${fmt.hora(ing.checkin_em)}</p>`
      : ing.status === 'cancelado' ? '<p class="ing-selo cancelado">Ingresso cancelado</p>' : '';
    const dados = [
      ['Data', fmt.ponto(ing.data)],
      ds.mostrar_lote ? ['Acesso', esc(ing.lote)] : null,
      ds.mostrar_local ? ['Local', esc(ing.local || '')] : null,
    ].filter(Boolean);
    return `
      <article class="ingresso clima-${esc(ds.clima)} ${ing.status !== 'valido' ? 'apagado' : ''}">
        <header class="ing-topo">${olho()}<span>ALL VISIONS</span></header>
        <p class="ing-edicao">${esc(ing.tema || ing.edicao || '')}</p>
        ${ds.mostrar_nome ? `<h2 class="ing-titular">${esc(ing.titular)}</h2>` : ''}
        <dl class="ing-dados">${dados.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
        ${ds.frase ? `<p class="ing-frase">${esc(ds.frase)}</p>` : ''}
        <div class="ing-entrada">
          <div class="ing-qr">${qrSvg(linhasQr) || '<span class="sem-qr">código</span>'}</div>
          <p class="ing-codigo">${esc(ing.codigo)}</p>
        </div>
        ${selo}
        ${ds.rodape ? `<footer class="ing-pe">${esc(ds.rodape)}</footer>` : ''}
      </article>`;
  }

  return { esc, fmt, api, olho, qrSvg, ingresso };
})();
