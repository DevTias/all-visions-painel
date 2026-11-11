# Painel ALL VISIONS

Painel de controle da festa: ingressos, promoters, automação, leituras dos dados e um laboratório com cinco ideias de expansão. Frontend em HTML, CSS e JavaScript puros; backend em Python com Flask e SQLite.

## Como abrir

Dois cliques em `iniciar.bat`. Na primeira vez ele prepara o ambiente (alguns segundos) e abre o painel em `http://127.0.0.1:5000`.

Pelo terminal, dentro desta pasta:

```
python -m venv "%LOCALAPPDATA%\all-visions-painel\venv"
"%LOCALAPPDATA%\all-visions-painel\venv\Scripts\python.exe" -m pip install -r requirements.txt
"%LOCALAPPDATA%\all-visions-painel\venv\Scripts\python.exe" app.py
```

O ambiente fica fora do OneDrive de propósito, para não sincronizar milhares de arquivos.

## O que é real e o que é ensaio

O painel abre em **modo ensaio**. O relógio fica parado em 17/04/2027, o 13º dia de venda da próxima edição, para a tela ter o que mostrar.

| Real (veio da memória da marca) | Ensaio (inventado para demonstrar) |
|---|---|
| Edição 1.0: 16/05/2026, Foccus Lounge, 120 pessoas | Quantidade de ingressos em cada lote da 2.0 |
| Preços dos lotes da 1.0: R$ 25, 35, 50, 70 e porta a R$ 120 | Compradores, com idade, cidade, gosto musical e bebida |
| Custos da 1.0: R$ 5.623,35, por categoria | Promoters, códigos, stories e vendas |
| Próxima edição: 01/05/2027, abertura das vendas em 05/04/2027 | Automações, tarefas, votos e comentários |
| Aprendizados da 1.0: bar, banheiros, 3º lote pequeno | |

No rodapé do menu lateral, **Começar do zero** apaga o ensaio, mantém só os fatos reais e passa a usar o relógio de hoje. **Voltar ao ensaio** faz o caminho inverso. As duas ações apagam o que estiver lançado, e o painel pede confirmação antes.

## As seções do painel

**Panorama.** A tela de todo dia. No topo, o painel diz em uma frase o que mais importa hoje (o ponto cego mais grave) e desenha a casa lugar por lugar: cada quadrado é um ingresso, colorido pelo lote. Abaixo: bilheteria, ritmo dos últimos 3 dias contra o ritmo necessário para lotar, projeção de fechamento, ticket médio, gráfico de venda dia a dia, pontos cegos, últimas vendas, próximos disparos e tarefas abertas. Atualiza sozinho a cada 6 segundos; o olho do menu pisca quando entra uma venda.

**Ingressos.** A escada de lotes em gráfico (largura é quantidade, altura é preço, área é o dinheiro que o degrau rende), a tabela de lotes editável na própria linha, criação de categorias novas (VIP, lista, 4º lote), registro de venda, lista de pedidos com busca e filtro, confirmação e estorno de pagamento, editor da aparência do e-ticket com prévia ao vivo e a portaria, que valida o código e marca a entrada. Quando um lote esgota, o próximo abre sozinho.

**Promoters.** Cadastro com código e link exclusivos, tabela de desempenho (vendas, receita, faixa, comissão, stories, dias sem vender), regra de comissão por faixas editável e a "visão dele": uma página simples que o promoter abre no celular com as próprias métricas, sem ver comprador nem colega.

**Automação.** Linha do tempo de tudo o que sai até a festa, fila de mensagens, posts e tarefas agendadas, gatilhos sempre ligados (a cada compra, a cada resposta), checagem automática do tom da marca em cada texto, lista de pessoas com recortes prontos (compradores, pendentes, veteranos da 1.0, estreantes, quem veio por promoter) e as tarefas da equipe em três colunas.

**Visões.** As leituras. Três frentes, cada uma com a conta que fez:
- *Leitura de preço*: quanto a escada inteira rende contra o custo da 1.0, se o lote aberto está segurando os seguintes, se o próximo degrau aguenta subir ou deve ser mantido, e a lição do 3º lote.
- *Leitura do público*: idade, cidade, origem, gosto musical, bebida, hora da compra, e o que isso pede de música, bar, cenografia e comunicação.
- *Pontos cegos*: riscos por nível (venda sem ritmo, promoter parado, pagamento pendente, banheiros sem responsável, falta de lembrete na véspera) com a ação sugerida a um toque.

**Laboratório.** As cinco ideias de expansão, cada uma com um protótipo funcionando. Detalhes mais abaixo.

### Páginas fora do painel

| Endereço | Para quem | O que faz |
|---|---|---|
| `/convite?ref=CODIGO` | Convidado | Compra em modo conceito. Mostra o lote aberto, pergunta gosto musical e bebida, emite o ingresso e credita o promoter do link. |
| `/ingresso/CODIGO` | Convidado | O e-ticket, com QR de verdade. |
| `/p/CODIGO` | Promoter | Vendas, comissão, posição, faixa, link e missões. |
| `/pista` | Quem está na festa | Votação ao vivo do próximo bloco. |

## Modelos de dados (simplificados)

| Tabela | Campos principais | Para que serve |
|---|---|---|
| `edicoes` | nome, tema, data, local, capacidade, abertura_vendas, status, publico_final | Cada edição da festa. |
| `custos` | edicao_id, categoria, valor | Gastos da edição; a 1.0 é a referência de custo. |
| `lotes` | edicao_id, nome, preco, quantidade, ordem, status | Categorias de ingresso. Status: aguardando, ativo, esgotado, pausado. |
| `pedidos` | lote_id, contato_id, promoter_id, quantidade, valor_total, metodo, status, criado_em | A transação. Status: pago, pendente, estornado. |
| `ingressos` | pedido_id, codigo, titular, status, checkin_em | Um por pessoa. Status: valido, usado, cancelado. |
| `contatos` | nome, instagram, cidade, faixa_etaria, genero_favorito, bebida, origem, veterano, tags, notas | A base de pessoas (CRM). |
| `promoters` | nome, instagram, codigo, ativo, entrou_em | Quem divulga. |
| `promoter_stories` | promoter_id, data | Stories registrados. |
| `comissao_faixas` | min_vendas, percentual, bonus, mimo | Regra de comissão por faixa. |
| `automacoes` | tipo, canal, titulo, conteudo, publico, gatilho, agendado_para, status, alcance | Mensagens, posts e tarefas agendadas. |
| `tarefas` | titulo, responsavel, prazo, status, origem, prioridade | Afazeres da equipe; origem manual ou automática. |
| `equipe` | nome, papel | Quem pode receber tarefa. |
| `votos` | opcao, criado_em | Votação da pista. |
| `feedbacks` | texto, nota, criado_em | Comentários pós-evento. |
| `config` | chave, valor | Modo (ensaio ou real), relógio do ensaio, aparência do ingresso. |

Regras que vivem no código, não na tabela:
- Estoque de um lote = quantidade − pagos − pendentes. Pedido pendente segura lugar.
- Comissão = receita paga com o código × percentual da faixa alcançada + bônus.
- Lote com 80% ocupado gera a tarefa "preparar virada"; lote esgotado abre o próximo e gera "anunciar virada".

## API

Tudo responde em JSON. Erros voltam como `{"erro": "mensagem"}`.

**Painel e configuração**

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/painel` | Resumo do panorama: métricas, lotes, últimas vendas, riscos, agenda. |
| GET | `/api/config` | Edição atual, histórico, equipe, públicos, aparência do ingresso. |
| POST | `/api/config/modo` | Troca entre ensaio e real (recria o banco). |
| PUT | `/api/config/ingresso` | Salva a aparência do e-ticket. |
| PATCH | `/api/edicao` | Edita nome, tema, data, local, capacidade, abertura. |

**Ingressos**

| Método | Rota | O que faz |
|---|---|---|
| GET, POST | `/api/lotes` | Lista com estoque; cria lote. |
| PATCH, DELETE | `/api/lotes/<id>` | Edita preço, quantidade, situação; apaga lote sem pedido. |
| GET, POST | `/api/pedidos` | Lista com filtro e busca; registra venda. |
| PATCH | `/api/pedidos/<id>` | Confirma pagamento ou estorna. |
| GET | `/api/ingressos/<codigo>` | Dados do e-ticket. |
| GET | `/api/ingressos/<codigo>/qr` | Matriz do QR. |
| GET, POST | `/api/checkin` | Contagem da portaria; valida e marca a entrada. |
| POST | `/api/ensaio/venda` | Só no ensaio: registra uma venda inventada. |

**Promoters**

| Método | Rota | O que faz |
|---|---|---|
| GET, POST | `/api/promoters` | Lista com métricas e comissão; cadastra e gera código. |
| PATCH, DELETE | `/api/promoters/<id>` | Edita, desliga, apaga (se não tiver venda). |
| POST | `/api/promoters/<id>/stories` | Registra um story de hoje. |
| PUT | `/api/comissoes` | Salva as faixas de comissão. |
| GET | `/api/promoters/codigo/<codigo>` | A visão simplificada do promoter. |

**Automação**

| Método | Rota | O que faz |
|---|---|---|
| GET, POST | `/api/automacoes` | Lista com alcance previsto e checagem de tom; cria. |
| PATCH, DELETE | `/api/automacoes/<id>` | Pausa, retoma, edita, apaga. |
| POST | `/api/automacoes/executar` | Dispara o que venceu (registra o disparo). |
| GET, POST | `/api/contatos` | Pessoas por recorte e busca; cadastra. |
| PATCH | `/api/contatos/<id>` | Etiquetas e anotações. |
| GET, POST | `/api/tarefas` | Lista; cria. |
| PATCH, DELETE | `/api/tarefas/<id>` | Muda situação, responsável, prazo; apaga. |

**Visões e laboratório**

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/visoes` | Métricas, leitura de preço, leitura do público, pontos cegos e premissas. |
| GET | `/api/lab/ranking` | Pontos, níveis e missões dos promoters. |
| GET, POST, DELETE | `/api/lab/votacao` | Resultado, voto, zerar a rodada. |
| POST | `/api/lab/texto` | Três versões de um texto, por objetivo. |
| POST | `/api/lab/checagem` | Confere um texto contra a voz da marca. |
| GET | `/api/lab/roteiro` | Roteiro da noite ajustado a lotação, energia, hora e voto. |
| GET, POST | `/api/lab/sentimento` | Mapa dos comentários por tema; soma um comentário. |

**Lado público**

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/publico/convite` | Lote aberto e quem convidou. |
| POST | `/api/publico/pedido` | Compra em modo conceito. |

## Como as leituras são calculadas

Nada é caixa-preta; cada leitura na tela tem um "Como li isso".

- **Ritmo base** = 60% da média dos últimos 3 dias + 40% da média dos últimos 7. Reage rápido sem se assustar com um dia ruim.
- **Ritmo necessário** = lugares que faltam ÷ dias até a festa.
- **Índice de demanda** = ritmo base ÷ ritmo necessário. Acima de 1,25, o próximo lote aguenta subir 10% (15% acima de 1,6). Abaixo de 0,8, o preço fica como está: o painel nunca sugere desconto, porque desconto não combina com a marca. Em vez disso sugere virada por data.
- **Projeção** = ritmo base até a festa, com os últimos 4 dias vendendo 1,8× (efeito de última semana). A faixa vai de "sem pico" a "pico de 2,4×". O 1,8 é uma premissa; depois da 2.0 dá para trocar pelo número real.
- **Custo de referência** = o que a 1.0 gastou. É a régua para saber quanto da festa a bilheteria já pagou.

## As cinco ideias do laboratório

Todas têm protótipo funcionando com regras simples. Em cada uma está dito onde um modelo de IA entra para levar a ideia adiante.

### 1. O jogo dos promoters

**O que é.** A campanha de vendas vira progressão. O promoter soma pontos (10 por ingresso, 4 por story, 5 por dia seguido postando), sobe de nível com nomes da casa (Vislumbre, Foco, Visão, Infinito) e recebe missões curtas: "três ingressos em três dias", "story três dias seguidos", "chegar à próxima faixa".

**Por que serve à ALL VISIONS.** O problema de promoter não é a primeira semana, é o meio da campanha, quando a novidade passa. Missão curta renova o fôlego sem aumentar comissão. E os níveis criam um ritual próprio, que é uma das metas da marca.

**O que o protótipo faz.** Calcula pontos, sequência e missões em cima das vendas e stories reais do painel. O promoter vê isso na página dele.

**Próximo passo com IA.** Missões personalizadas: um modelo olha o histórico de cada promoter (em que dia e hora ele vende, para que tipo de público) e propõe a missão com mais chance de ser cumprida. Também detecta sozinho o promoter que está esfriando antes de ele parar.

**Cuidado.** Ranking aberto pode gerar spam. Por isso cada promoter vê só a própria posição, e os pontos valem story, não quantidade de mensagens.

### 2. A pista decide

**O que é.** Durante a festa, quem está dentro vota no rumo do próximo bloco pelo celular, lendo um QR na pulseira ou no cardápio. O resultado aparece em tempo real para os DJs.

**Por que serve.** Dá voz ao público sem entregar a curadoria: só entram os gêneros da casa (House, Deep House, Indie Dance, Melodic House, Tech House, Progressive House). A pista escolhe o caminho, não o destino. Reforça a união, que é um dos inegociáveis.

**O que o protótipo faz.** Página `/pista` com um voto por rodada, barras ao vivo e painel para zerar a rodada.

**Próximo passo com IA.** Cruzar o voto com o que foi tocado e com a reação da pista para sugerir a faixa de transição, e abrir outras perguntas além de gênero (mais grave ou mais melódico, subir ou respirar). Uma camada social leve cabe aqui: mural de fotos da noite visível só para quem fez check-in.

**Cuidado.** Um voto por ingresso, liberado só depois da entrada, para ninguém de fora votar.

### 3. Estúdio de texto

**O que é.** Gerador de legendas, mensagens e roteiros no tom da casa. Para cada objetivo (abertura, virada de lote, revelação, lembrete, agradecimento) entrega três versões em níveis de mistério: claro, velado e enigma. Junto, uma checagem que barra o que soa como festa comum.

**Por que serve.** A regra da marca é revelar aos poucos e nunca soar comercial. A checagem transforma essa regra em algo verificável: acusa "imperdível", "bombando", emoji, exclamação em excesso, caixa alta, texto longo demais, e confere se o texto toca em visão, olhar ou percepção.

**O que o protótipo faz.** Combina frases-base escritas no tom da marca com os dados da edição (data, lote, preço). A checagem roda em qualquer texto, inclusive nas automações.

**Próximo passo com IA.** Trocar as frases-base por um modelo de linguagem que recebe o guia de voz da marca e o contexto do dia (lote aberto, ritmo, o que já foi revelado) e escreve do zero. A checagem continua igual e vira o filtro de saída: nada vai para a fila sem passar. O mesmo vale para roteiro de reels, pauta de TikTok e descrição de arte.

**Cuidado.** O modelo propõe, a pessoa aprova. Nenhum texto sai sozinho.

### 4. Roteiro vivo

**O que é.** O roteiro da noite deixa de ser uma tabela fixa. Três sinais o reordenam: quantos por cento da casa já entraram (vem da portaria), a energia da pista e o voto do público.

**Por que serve.** Gastar o pico com a casa pela metade é o erro mais caro de uma noite. Com o check-in alimentando o roteiro, o pico espera a casa encher. E a operação entra junto: casa acima de 70% dispara a ronda dos banheiros, que foi o ponto fraco da 1.0.

**O que o protótipo faz.** Regras claras: casa abaixo de 60% perto do pico empurra o pico uma hora; casa cheia com pista morna antecipa; energia no teto depois do pico encurta o respiro; o voto só mexe em bloco flexível (subida e virada), nunca em pico, respiro ou fechamento.

**Próximo passo com IA.** Medir a energia sem depender de alguém mover um controle: som ambiente, fluxo no bar, movimento na pista. E aprender entre edições em que hora a casa realmente enche.

**Cuidado.** O roteiro sugere, o DJ decide. A curadoria é da casa.

### 5. Leitura pós-evento

**O que é.** No dia seguinte, a mensagem de agradecimento pede uma frase sobre a noite. As respostas viram mapa: por tema (decoração, som, bar, banheiros, público, ingressos, estrutura), quantos elogios e quantas críticas, e duas listas, repetir e corrigir.

**Por que serve.** A 1.0 deixou três aprendizados que hoje estão na memória de quem fez a festa. Com a leitura, eles passam a vir do público, com contagem, e alimentam os pontos cegos da edição seguinte.

**O que o protótipo faz.** Classifica cada comentário por um léxico de palavras positivas e negativas e por palavras-chave de tema. Os comentários de partida são simulados, escritos em cima do que a 1.0 ensinou.

**Próximo passo com IA.** Um modelo de linguagem entende ironia, gíria e comentário misto ("amei, mas a fila do bar..."), resume em uma página o que mudou de uma edição para outra e lê também menções em stories e comentários do Instagram.

**Cuidado.** Poucos comentários enganam. O painel mostra a contagem ao lado de cada tema.

### Outras ideias em aberto

- **Lista de espera com repasse oficial.** Lote esgotado abre fila; ingresso estornado vai para o próximo da fila pelo preço original. Mantém a exclusividade sem cambista.
- **Passaporte de edições.** O contato guarda em quais edições esteve. Veterano recebe a abertura algumas horas antes e um sinal físico na noite.
- **Preço que aprende.** Depois de duas ou três edições, o índice de demanda e o pico da última semana deixam de ser premissa e passam a ser medidos.

## Antes de usar de verdade

1. **Acesso.** Hoje o painel não pede senha e só responde no próprio computador. Para colocar na internet, precisa de login no painel e de limite de pedidos nas páginas públicas.
2. **Pagamento.** A venda é um registro. Ao ligar um meio de pagamento (Pix, cartão), é ele quem muda o pedido de pendente para pago, pela rota `PATCH /api/pedidos/<id>`.
3. **Canais.** Os disparos são registrados, não enviados. Para enviar, ligue cada canal a `POST /api/automacoes/executar`: WhatsApp, e-mail e agendamento de posts.
4. **Dados pessoais.** A base guarda nome, Instagram e preferências. Avise na compra para que isso é usado e ofereça como sair da lista.
5. **Cópia de segurança.** O banco é o arquivo `dados/painel.db`. Copiar esse arquivo é o backup.

## Arquivos

```
app.py           rotas e regras de venda, comissão e automação
banco.py         esquema do banco, relógio e utilitários
ensaio.py        carga inicial: fatos reais e dados de ensaio
visoes.py        leituras: preço, público e pontos cegos
laboratorio.py   as cinco ideias
templates/       painel.html e publico.html
static/css       painel.css
static/js        comum.js, painel.js, publico.js
static/fonts     Oslla e Montserrat
```
