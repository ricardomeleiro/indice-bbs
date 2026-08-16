# CLAUDE.md — Índice BBS

Este arquivo orienta o Claude Code ao trabalhar neste repositório.

## O que é

Aplicação para acompanhamento do **Índice BBS** por embarcação/ROV — coleta mensal
de Total BBS, Não Conformes e falhas por critério (C1/C2/C3/C4-CRM/C4-Elo),
com dashboard, relatórios e Pareto. Substitui a planilha
`Indice_BBS_por_Embarcacao_v10_ATUALIZADA.xlsx`.

**Stack:** FastAPI + Jinja2 + Bootstrap 5 + Chart.js | PostgreSQL 16 | Docker Compose

## Rodando local

```bash
cp .env.example .env       # ajuste POSTGRES_PASSWORD e habilite DEV_MODE=1
docker compose up --build
# http://localhost:18010  (fora do Hub — usa DEV_USER_EMAIL do .env)
```

## Deploy na EC2 (hub.c-innovation.com.br/bbs)

1. Copie o repo para `/home/ubuntu/indice-bbs/` na EC2 (18.188.46.180)
2. Copie `.env.example` para `.env`, ajuste senha e SET `DEV_MODE=0`
3. `docker compose up -d --build`
4. Configure o Authentik:
   - **Applications** → New: `Índice BBS`, slug `indice-bbs`
   - **Providers** → New: **Proxy Provider** modo *Forward auth (single application)*
   - **External host:** `https://hub.c-innovation.com.br/bbs`
   - Attach ao Embedded Outpost
   - (opcional) Crie grupos `bbs-admin` e `bbs-editor`
5. Edite `/etc/apache2/sites-available/hub.c-innovation.com.br.conf` e adicione
   o bloco de [deployment/apache-bbs-subpath.conf](deployment/apache-bbs-subpath.conf)
   ANTES do `ProxyPass /` existente
6. `sudo apache2ctl configtest && sudo systemctl reload apache2`
7. Acesse `https://hub.c-innovation.com.br/bbs/`

## Importar planilha existente

```bash
docker cp /caminho/local/Indice_BBS_por_Embarcacao_v10_ATUALIZADA.xlsx indicebbs_app:/tmp/bbs.xlsx
docker exec -it indicebbs_app python import_xlsx.py /tmp/bbs.xlsx
```

## Arquitetura

```
app/
  main.py                — FastAPI (root_path=/bbs) + exception handlers
  init_db.py             — cria tabelas e faz seed de embarcações/ROVs
  seed_data.py           — dados extraídos da aba "Cadastro_ROV"
  import_xlsx.py         — importador do histórico da planilha
  config.py              — pydantic-settings a partir do .env
  database.py            — engine + Session + Base
  dependencies.py        — require_login / require_editor / require_admin
  models/
    user.py, vessel.py, rov.py, entry.py, maturity.py, audit.py
  routers/
    dashboard.py         — /dashboard (mensal, KPI% × meta)
    entries.py           — /entries CRUD
    reports.py           — /reports/{evolucao,pareto,ranking,heatmap,contratante}
    admin.py             — /admin/{vessels,maturidade,users,audit}
    exports.py           — /export/entries.csv
  services/
    auth_headers.py      — resolve o usuário pelos headers X-Authentik-*
    kpi.py               — agregações (rollup por embarcação/mês/ano)
  static/css/custom.css
  templates/             — Jinja2 + Bootstrap 5
deployment/
  apache-bbs-subpath.conf
```

## Papéis

| Papel   | Pode |
|---------|------|
| viewer  | Dashboard, relatórios, exportar CSV |
| editor  | Tudo de viewer + inserir/editar/excluir lançamentos |
| admin   | Tudo + gerenciar embarcações, maturidade SMS, usuários, auditoria |

Papel é atribuído automaticamente a partir dos grupos Authentik configurados em
`BBS_ADMIN_GROUP` / `BBS_EDITOR_GROUP`. Um admin promovido manualmente pela
tela **/admin/users** mantém o cargo mesmo se sair dos grupos (proteção contra
lockout).

## Meta de KPI

A meta anual por embarcação vem da maturidade SMS (tabela `vessel_maturities`):

| Maturidade | Meta |
|---|---|
| Inicial    | 80% |
| Estável    | 87% |
| Maduro     | 92% |

Ajustada em `/admin/maturidade?ano=YYYY`. Padrão quando nada foi definido: Inicial.

## Diretório da planilha original (referência)

`/Users/rdm/Library/CloudStorage/GoogleDrive-ricardomeleiro@gmail.com/Meu Drive/Claude/KPI/Indice_BBS_por_Embarcacao_v10_ATUALIZADA.xlsx`
