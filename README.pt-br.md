# Automação de Conciliação de Pagamentos

Projeto em Python desenvolvido a partir de uma necessidade operacional real de uma empresa brasileira: conferir comprovantes de pagamento e localizar os lançamentos correspondentes no contas a pagar de um ERP.

A solução integra extração de dados de comprovantes, regras determinísticas de conciliação, API do Tiny/Olist ERP e persistência local para reduzir conferências repetitivas e controlar o risco de processamento duplicado.

> **Estado atual (19/10/2026):** núcleo de conciliação e adaptador Telegram implementados, com testes automatizados e validação local em **dry-run**. A instalação, o aceite operacional e a habilitação de baixas financeiras automáticas no cliente permanecem pendentes. O Telegram publicado **não solicita baixas**.

## Funcionalidades implementadas

- **Leitura de comprovantes:** extração de texto nativo de PDFs com `pypdf` e OCR de imagens PNG/JPG/JPEG com Google Cloud Vision.
- **Extração estruturada:** identificação de provedor, tipo de pagamento, valor, data, documento do beneficiário e identificadores de transação, quando disponíveis.
- **Validação de imagens de boletos:** nos layouts elegíveis do Mercado Pago, o valor identificado por OCR precisa coincidir com o valor codificado no código de barras.
- **Consulta ao ERP:** autenticação OAuth 2.0, renovação de tokens e consulta paginada de contas a pagar pela API v3 do Tiny/Olist.
- **Matching determinístico:** correspondência por CPF/CNPJ completo, saldo em aberto igual ao valor pago e vencimento dentro de uma janela padrão de **±10 dias corridos** em relação à data do pagamento. Apenas uma correspondência única pode avançar.
- **Controle de duplicidade:** registro em SQLite e verificação por hash do arquivo e identificadores financeiros, quando disponíveis.
- **Tratamento de incerteza:** transações ambíguas, incompletas ou com resultado remoto inconclusivo são direcionadas para revisão ou verificação, sem repetição automática de uma baixa.
- **Retorno estruturado:** a função principal devolve um dicionário com status, mensagem e campos de diagnóstico para interfaces de operação.
- **Integração Telegram:** bot por long polling, grupo e remetentes autorizados, recebimento de PDF/JPG/JPEG/PNG, validação de formato, limite de 10 MB, arquivos temporários descartáveis e respostas resumidas sem documentos financeiros.

## Escopo e limitações do MVP

O processamento automático é restrito aos comprovantes e layouts explicitamente reconhecidos. O **Mercado Pago** foi priorizado como recorte inicial do MVP, com base no fluxo de comprovantes observado na operação real. Essa decisão permite validar a conciliação e os controles financeiros antes de ampliar o suporte a outros emissores. A implementação atual não oferece suporte genérico a documentos de outros bancos ou provedores.

Para imagens, os layouts de boleto `mp_pag_bol` e `mp_pix_bol` dependem da validação do código de barras. Transferências Pix em imagem (`mp_pix_tra`) e layouts não reconhecidos são encaminhados à revisão manual. A extração de dados de um documento **não significa**, por si só, autorização para baixa.

O projeto **não cria contas a pagar ausentes** no ERP. Quando não existe correspondência, o resultado é `no_match`. Também não automatiza os processos fiscais, a classificação contábil, os cartões ou o fluxo completo de contas a pagar da empresa.

## Arquitetura e fluxo de processamento

```text
Comprovante PDF / imagem
          |
          v
Extração de texto (pypdf / Google Cloud Vision)
          |
          v
Parser e validações do comprovante
          |
          v
Identificação e deduplicação (SQLite)
          |
          v
Consulta de contas a pagar (Tiny API v3)
          |
          v
Matching determinístico
          |
          +--> Dados insuficientes / ambiguidade --> revisão manual
          |
          +--> Sem correspondência -------------> no_match
          |
          v
Correspondência única
          |
          +--> Modo padrão (settlement_enabled=False) --> dry_run
          |
          +--> Baixa explicitamente habilitada
                       |
                       v
                 Solicitação ao Tiny
                       |
                       v
                 Consulta de confirmação
                       |
                       v
                 Atualização do estado local
```

A orquestração está em `src/main.py`. A consulta e a baixa financeira são operações distintas: uma resposta HTTP de sucesso à solicitação de baixa não substitui a verificação posterior do estado da conta no Tiny.

## Tecnologias e conceitos aplicados

| Tecnologia | Utilização |
| --- | --- |
| Python | Orquestração e regras de negócio |
| `pypdf` | Extração de texto de PDFs com texto nativo |
| Google Cloud Vision | OCR de comprovantes em imagem |
| `requests` | Comunicação HTTP com OAuth e API do Tiny |
| Tiny/Olist ERP API v3 | Consulta de contas a pagar e integração financeira |
| SQLAlchemy + SQLite | Persistência local, estados e controle de duplicidade |
| `python-dotenv` | Carregamento de configuração local |
| `python-telegram-bot` | Recepção e resposta a comprovantes em grupo privado do Telegram |
| `pytest` | Testes automatizados |

As decisões de correspondência e elegibilidade são implementadas por regras explícitas, não por um modelo de IA que decide autonomamente se uma conta deve ser baixada.

## Instalação e configuração

**Pré-requisitos:** Python compatível com as dependências fixadas em `requirements.txt`, acesso autorizado à API v3 do Tiny/Olist ERP e, para processar imagens, credenciais válidas do Google Cloud Vision. O projeto foi desenvolvido para execução local; a instalação operacional no computador da empresa ainda não foi finalizada.

Clone o repositório e entre no diretório do projeto:

```bash
git clone https://github.com/vagner-lcf/payment-reconciliation-automation.git
cd payment-reconciliation-automation
```

Crie e ative um ambiente virtual no Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha as variáveis do fluxo OAuth e, se utilizar o bot, as configurações do Telegram:

```dotenv
OLIST_CLIENT_ID=<seu_client_id>
OLIST_CLIENT_SECRET=<seu_client_secret>
OLIST_REDIRECT_URI=http://localhost:8000/callback
TELEGRAM_BOT_TOKEN=<token_do_bot>
TELEGRAM_ALLOWED_CHAT_ID=<id_do_grupo_privado>
TELEGRAM_ALLOWED_USER_IDS=<id_usuario_1>,<id_usuario_2>
```

A URI de redirecionamento deve corresponder à cadastrada no aplicativo OAuth e à configuração do callback local, que utiliza a porta `8000`. **Não compartilhe valores reais dessas variáveis.**

Para o OCR de imagens, configure a autenticação do Google Cloud Vision no ambiente de execução, conforme o método de credenciais adotado para o projeto Google Cloud. PDFs com texto nativo não dependem do serviço de OCR.

Para autorizar o acesso ao Tiny pela primeira vez ou reautorizar quando necessário, execute:

```powershell
python -m src.authorize_tiny
```

O navegador será aberto para a autorização. Os tokens retornados são armazenados localmente em `data/tiny_tokens.json`, ignorado pelo Git. O sistema tenta renovar o acesso automaticamente; caso a autorização seja revogada ou a renovação falhe, é necessária nova autorização manual.

> **Segurança:** os tokens persistidos em arquivo não são criptografados pelo projeto. Restrinja o acesso ao computador e à pasta de execução. O arquivo `.env.example` contém somente valores fictícios. O `.env` real e o diretório `data/` estão ignorados pelo Git.

## Execução em modo seguro

A interface programática atual é `main(file_path: str, settlement_enabled: bool = False)`. Não há, nesta versão, um comando de terminal com argumentos configuráveis para escolher o comprovante.

Na raiz do projeto, execute o Python e chame a função com o caminho de um arquivo de teste autorizado:

```python
from src.main import main

result = main(
    file_path="data/input/comprovante_exemplo.pdf",
    settlement_enabled=False,
)

print(result["status"])
print(result["message"])
```

O caminho acima é **ilustrativo**: substitua-o por um comprovante de teste existente. A execução em `dry_run` **não solicita a baixa**, mas ainda pode acessar a API do Tiny, consumir OCR pago no caso de imagens e registrar informações no SQLite local.

**Não habilite `settlement_enabled=True` em ambiente financeiro real apenas para experimentar.** A operação contínua depende da conclusão dos testes de segurança, procedimentos de recuperação e autorização do responsável.

## Operação pelo Telegram (dry-run)

Execute a partir da raiz do projeto, após configurar `.env` e concluir a autorização inicial do Tiny:

```powershell
python -m src.telegram_bot
```

O bot utiliza **long polling**: mantenha **apenas uma instância** em execução. Ele recebe fotos ou documentos PDF, JPG, JPEG e PNG de remetentes autorizados no grupo privado. A autorização exige simultaneamente `TELEGRAM_ALLOWED_CHAT_ID` e o ID do remetente em `TELEGRAM_ALLOWED_USER_IDS` (separados por vírgula). Outros tipos de mensagem não são processados.

O adaptador limita o tamanho a **10 MB**, confere extensão e MIME de documentos e valida a assinatura inicial do arquivo após o download. Os arquivos são armazenados temporariamente e descartados após o processamento. O núcleo é executado em thread auxiliar, com bloqueio para serializar conciliações dentro da instância. Não há fila durável nem garantia de recuperação de mensagens após queda de energia ou reinício.

**Restrição atual:** a chamada ao núcleo usa `settlement_enabled=False` de forma fixa. A variável `SETTLEMENT_ENABLED` **não existe** nesta versão. Em produção homologada, a configuração da autorização de baixa deverá ser implementada e testada separadamente; não basta alterar o `.env` atual. A usuária operacional não precisará liberar cada comprovante depois que o fluxo autorizado estiver implantado.

As respostas do bot não reproduzem o dicionário financeiro completo, mas o mapeamento atual utiliza principalmente `status`; alguns motivos (`reason`), como indisponibilidade de autenticação ou conta com baixa pendente, ainda requerem tratamento operacional mais específico.

## Resultados e estados do processamento

A função principal retorna um dicionário com `status`, `message`, `reason`, `transaction_id`, `id_tiny`, `beneficiary_document`, `payment_date` e `amount`.

| Status | Significado resumido |
| --- | --- |
| `dry_run` | Correspondência identificada, sem solicitar baixa financeira |
| `processed` | Baixa confirmada no Tiny e estado local atualizado |
| `already_processed` | Transação já registrada como processada |
| `already_in_review` | Transação já encaminhada à revisão |
| `review_required` | Dados ou layout não elegíveis para automação |
| `no_match` | Nenhuma conta correspondente encontrada |
| `ambiguous_match` | Mais de uma correspondência possível |
| `verification_pending` | Resultado financeiro ou atualização local exige conferência antes de prosseguir |
| `error` | Falha de processamento ou integração identificada |

O campo `reason` complementa determinados resultados. Os campos de documento e identificadores são destinados ao uso interno e **não devem ser enviados integralmente a chats, logs públicos ou capturas de tela**.

## Segurança e tratamento de falhas

- **Baixa desabilitada por padrão:** `settlement_enabled=False` é o comportamento seguro da função principal.
- **Identidade financeira:** o hash do arquivo e os identificadores de transação ajudam a impedir processamento repetido de um mesmo pagamento.
- **Estados persistidos:** `processing`, `processed` e `review_required` permitem distinguir processamento pendente, concluído e casos que precisam de intervenção.
- **Proteção contra baixa duplicada:** transações pendentes associadas a uma mesma conta do Tiny são consideradas antes de uma nova tentativa.
- **Confirmação remota:** a baixa só é considerada confirmada quando o estado da conta é consultado novamente no ERP.
- **Falhas inconclusivas:** timeout ou erro após solicitar uma baixa **não prova que ela não ocorreu**. A recuperação deve verificar o Tiny e o registro local, sem repetir automaticamente o POST financeiro.

Ainda estão pendentes a validação completa do contrato financeiro da API em cenários de falha, procedimentos operacionais de recuperação, testes de acesso com os usuários finais e revisão dos dados apresentados em logs e mensagens. O `main()` ainda possui saídas `print()` potencialmente sensíveis; o bot não deve repassá-las ao grupo.

## Testes

A suíte automatizada utiliza `pytest`. Execute na raiz do repositório:

```powershell
python -m pytest -q
```

Os testes cobrem componentes como extração, parsing, matching, integração simulada e persistência. O desenvolvimento também incluiu validações pontuais com documentos e contas reais, em condições controladas.

**Referência de desenvolvimento (19/10/2026):** 183 testes aprovados na execução local informada pelo desenvolvedor. O resultado não representa uma execução independente desta auditoria.

## Estrutura do projeto

```text
payment-reconciliation-automation/
├── src/
│   ├── main.py                     # Orquestração do processamento
│   ├── telegram_bot.py             # Interface Telegram em dry-run
│   ├── receipt_parser.py           # Extração estruturada dos dados
│   ├── pdf_text_extractor.py       # Leitura de PDF
│   ├── image_text_extractor.py     # OCR de imagens
│   ├── receipt_hash_extractor.py   # Identificação por hash
│   ├── matching.py                 # Regras de correspondência
│   ├── tiny_client.py              # Integração com a API do ERP
│   ├── auth.py                     # Fluxos OAuth
│   ├── authorize_tiny.py           # Autorização manual
│   ├── callback.py                 # Callback OAuth local
│   ├── token_manager.py            # Renovação dos tokens
│   ├── token_store.py              # Persistência dos tokens
│   └── tratoray_transactions_db.py # Persistência das transações
├── tests/                          # Testes automatizados
├── scripts/                        # Diagnósticos manuais
├── data/                           # Dados locais (ignorados pelo Git)
├── requirements.txt
└── README.pt-br.md
```

A estrutura apresenta os principais componentes, não uma listagem exaustiva. Arquivos de dados, comprovantes, banco SQLite e tokens locais não devem ser versionados.

## Estado atual e próximos passos

O núcleo e a integração Telegram em dry-run estão implementados. As próximas etapas são validar a operação e a recuperação de falhas no ambiente do cliente, revisar os retornos operacionais, conferir o contrato financeiro do Tiny e implementar a habilitação explícita de baixas somente após homologação. A instalação contínua, a transferência de controle do bot e a medição dos resultados reais permanecem pendentes.

A eventual publicação deste repositório dependerá de uma revisão de confidencialidade e da autorização para divulgar o projeto como case profissional. Esta documentação não implica autorização para executar baixas financeiras em produção.
