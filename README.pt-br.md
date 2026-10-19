# Automação de Conciliação de Pagamentos

Projeto em Python desenvolvido a partir de uma necessidade operacional real de uma empresa brasileira: conferir comprovantes de pagamento e localizar os lançamentos correspondentes no contas a pagar de um ERP.

A solução integra extração de dados de comprovantes, regras determinísticas de conciliação, API do Tiny/Olist ERP e persistência local para reduzir conferências repetitivas e controlar o risco de processamento duplicado.

> **Estado atual:** núcleo de processamento local implementado e validado em cenários controlados. Integração Telegram e operação contínua ainda não concluídas. A baixa financeira permanece **desabilitada por padrão**.

## Funcionalidades implementadas

- **Leitura de comprovantes:** extração de texto nativo de PDFs com `pypdf` e OCR de imagens PNG/JPG/JPEG com Google Cloud Vision.
- **Extração estruturada:** identificação de provedor, tipo de pagamento, valor, data, documento do beneficiário e identificadores de transação, quando disponíveis.
- **Validação de imagens de boletos:** nos layouts elegíveis do Mercado Pago, o valor identificado por OCR precisa coincidir com o valor codificado no código de barras.
- **Consulta ao ERP:** autenticação OAuth 2.0, renovação de tokens e consulta paginada de contas a pagar pela API v3 do Tiny/Olist.
- **Matching determinístico:** correspondência por CPF/CNPJ completo, saldo em aberto igual ao valor pago e vencimento dentro de uma janela padrão de **±10 dias corridos** em relação à data do pagamento. Apenas uma correspondência única pode avançar.
- **Controle de duplicidade:** registro em SQLite e verificação por hash do arquivo e identificadores financeiros, quando disponíveis.
- **Tratamento de incerteza:** transações ambíguas, incompletas ou com resultado remoto inconclusivo são direcionadas para revisão ou verificação, sem repetição automática de uma baixa.
- **Retorno estruturado:** a função principal devolve um dicionário com status, mensagem e campos de diagnóstico para futuras interfaces de operação.

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
| `pytest` | Testes automatizados |

As decisões de correspondência e elegibilidade são implementadas por regras explícitas, não por um modelo de IA que decide autonomamente se uma conta deve ser baixada.

## Instalação e configuração

**Pré-requisitos:** Python compatível com as dependências fixadas em `requirements.txt`, acesso autorizado à API v3 do Tiny/Olist ERP e, para processar imagens, credenciais válidas do Google Cloud Vision. O projeto foi desenvolvido para execução local; a instalação operacional no computador da empresa ainda não foi finalizada.

Clone o repositório e entre no diretório do projeto:

```bash
git clone <URL_DO_REPOSITORIO>
cd payment-reconciliation-automation
```

Crie e ative um ambiente virtual no Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto com as variáveis utilizadas pelo fluxo OAuth:

```dotenv
OLIST_CLIENT_ID=<seu_client_id>
OLIST_CLIENT_SECRET=<seu_client_secret>
OLIST_REDIRECT_URI=<sua_uri_de_redirecionamento_local>
```

A URI de redirecionamento deve corresponder à cadastrada no aplicativo OAuth e à configuração do callback local, que utiliza a porta `8000`. **Não compartilhe valores reais dessas variáveis.**

Para o OCR de imagens, configure a autenticação do Google Cloud Vision no ambiente de execução, conforme o método de credenciais adotado para o projeto Google Cloud. PDFs com texto nativo não dependem do serviço de OCR.

Para autorizar o acesso ao Tiny pela primeira vez ou reautorizar quando necessário, execute:

```powershell
python -m src.authorize_tiny
```

O navegador será aberto para a autorização. Os tokens retornados são armazenados localmente em `data/tiny_tokens.json`, ignorado pelo Git. O sistema tenta renovar o acesso automaticamente; caso a autorização seja revogada ou a renovação falhe, é necessária nova autorização manual.

> **Segurança:** os tokens persistidos em arquivo não são criptografados pelo projeto. Restrinja o acesso ao computador e à pasta de execução. O arquivo `.env.example` ainda não foi criado; os nomes de variáveis acima foram conferidos diretamente em `src/auth.py`.

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

Ainda estão pendentes a validação completa do contrato financeiro da API em cenários de falha, procedimentos operacionais de recuperação, controle de acesso do futuro bot e revisão dos dados apresentados em logs e mensagens.

## Testes

A suíte automatizada utiliza `pytest`. Execute na raiz do repositório:

```powershell
python -m pytest -q
```

Os testes cobrem componentes como extração, parsing, matching, integração simulada e persistência. O desenvolvimento também incluiu validações pontuais com documentos e contas reais, em condições controladas.

**Referência de desenvolvimento:** 162 testes aprovados na execução local informada pelo desenvolvedor até a última consolidação do projeto. Esse número não representa uma execução independente durante a elaboração deste README e deve ser atualizado conforme a suíte evoluir.

## Estrutura do projeto

```text
payment-reconciliation-automation/
├── src/
│   ├── main.py                     # Orquestração do processamento
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

O núcleo de conciliação local está implementado. As próximas etapas previstas são a integração com Telegram em modo seguro, a validação da experiência de uso, o endurecimento dos controles operacionais e financeiros e a medição de resultados no processo real.

A eventual publicação deste repositório dependerá de uma revisão de confidencialidade e da autorização para divulgar o projeto como case profissional. Esta documentação não implica autorização para executar baixas financeiras em produção.
