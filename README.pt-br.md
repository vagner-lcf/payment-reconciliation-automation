# Automação de Conciliação de Pagamentos

Projeto em Python desenvolvido a partir de uma necessidade operacional real: conferir comprovantes de pagamento, localizar os lançamentos correspondentes no contas a pagar do Tiny/Olist ERP e, quando autorizado, realizar a baixa financeira de forma controlada.

A solução integra extração de dados de comprovantes, regras determinísticas de conciliação, API do Tiny/Olist ERP e persistência local para reduzir conferências repetitivas e controlar o risco de processamento duplicado.

> **Estado atual — 20/10/2026:** núcleo de conciliação e integração Telegram implementados, com **198 testes automatizados aprovados**. Uma baixa financeira real foi realizada em teste controlado e confirmada no Tiny. A configuração de baixa automática pelo Telegram está implementada, com modo seguro por padrão. A instalação e a homologação operacional no computador do cliente permanecem pendentes.

## Funcionalidades implementadas

- **Leitura de comprovantes:** extração de texto nativo de PDFs com `pypdf` e OCR de imagens PNG/JPG/JPEG com Google Cloud Vision.
- **Extração estruturada:** identificação de provedor, tipo de pagamento, valor, data, documento do beneficiário e identificadores de transação, quando disponíveis.
- **Validação de imagens de boletos:** nos layouts elegíveis do Mercado Pago, o valor identificado por OCR precisa coincidir com o valor codificado no código de barras.
- **Consulta ao ERP:** autenticação OAuth 2.0, renovação de tokens e consulta paginada de contas a pagar pela API v3 do Tiny/Olist.
- **Matching determinístico:** correspondência por CPF/CNPJ completo, saldo em aberto igual ao valor pago e vencimento dentro de uma janela de **±10 dias corridos** em relação à data do pagamento. Apenas uma correspondência única pode avançar.
- **Controle de duplicidade:** registro em SQLite e verificação por hash do arquivo e identificadores financeiros, quando disponíveis.
- **Tratamento de incerteza:** transações ambíguas, incompletas ou com resultado remoto inconclusivo são direcionadas para revisão ou verificação, sem repetição automática de uma baixa.
- **Retorno estruturado:** a função principal devolve um dicionário com status, mensagem e campos de diagnóstico para interfaces de operação.
- **Integração Telegram:** bot por long polling, grupo e remetentes autorizados, recebimento de PDF/JPG/JPEG/PNG, validação de formato, limite de 10 MB e arquivos temporários descartáveis.
- **Respostas operacionais:** mensagens com indicadores visuais, CPF/CNPJ, valor e data do pagamento, quando disponíveis, facilitando a conferência manual no Tiny.
- **Modo de operação configurável:** habilitação ou desabilitação de baixas financeiras pelo Telegram por meio da variável `SETTLEMENT_ENABLED`.

## Escopo e limitações do MVP

O processamento automático é restrito aos comprovantes e layouts explicitamente reconhecidos. O **Mercado Pago** foi priorizado como recorte inicial do MVP, com base no fluxo de comprovantes observado na operação real.

Essa decisão permite validar a conciliação e os controles financeiros antes de ampliar o suporte a outros emissores. A implementação atual não oferece suporte genérico a documentos de outros bancos ou provedores.

Para imagens, os layouts de boleto `mp_pag_bol` e `mp_pix_bol` dependem da validação do código de barras.

**Transferências Pix em imagem (`mp_pix_tra`) são encaminhadas intencionalmente à revisão manual.** Nesses comprovantes, documentos de beneficiários frequentemente aparecem mascarados e a apresentação do valor não oferece a mesma validação disponível nos boletos com código de barras. Portanto, a extração dos dados não é considerada suficiente para autorizar uma baixa automática.

Layouts não reconhecidos e comprovantes com informações obrigatórias ausentes também são direcionados à revisão manual.

O projeto **não cria contas a pagar ausentes** no ERP. Quando não existe correspondência, o resultado é `no_match`. Também não automatiza processos fiscais, classificação contábil, cartões ou o fluxo completo de contas a pagar da empresa.

### Critério de engenharia do MVP

O objetivo é entregar uma solução **suficientemente segura e confiável para o uso cotidiano**, priorizando riscos plausíveis de baixa indevida ou duplicada, indisponibilidade operacional e dificuldades de recuperação.

Medidas adicionais de segurança e complexidade técnica devem ser justificadas pelo risco real, impacto e custo de implementação. Não faz parte do objetivo proteger a aplicação contra todas as falhas teoricamente possíveis.

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
          +--> Inelegível / dados insuficientes --> revisão manual
          |
          v
Consulta de contas a pagar (Tiny API v3)
          |
          v
Matching determinístico
          |
          +--> Sem correspondência -------------> no_match
          |
          +--> Correspondência ambígua ---------> revisão manual
          |
          v
Correspondência única e elegível
          |
          +--> Modo seguro (settlement_enabled=False) --> dry_run
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

A orquestração está em `src/main.py`. O adaptador Telegram está em `src/telegram_bot.py` e não replica as regras de conciliação.

A consulta e a baixa financeira são operações distintas: uma resposta HTTP de sucesso à solicitação de baixa não substitui a verificação posterior do estado da conta no Tiny.

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

As decisões de correspondência e elegibilidade são implementadas por **regras explícitas**, não por um modelo de IA que decide autonomamente se uma conta deve ser baixada.

## Instalação e configuração

**Pré-requisitos:** Python compatível com as dependências de `requirements.txt`, acesso autorizado à API v3 do Tiny/Olist ERP e, para processar imagens, credenciais válidas do Google Cloud Vision.

Clone o repositório:

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

Copie `.env.example` para `.env` e configure as variáveis necessárias:

```dotenv
OLIST_CLIENT_ID=<seu_client_id>
OLIST_CLIENT_SECRET=<seu_client_secret>
OLIST_REDIRECT_URI=http://localhost:8000/callback

TELEGRAM_BOT_TOKEN=<token_do_bot>
TELEGRAM_ALLOWED_CHAT_ID=<id_do_grupo_privado>
TELEGRAM_ALLOWED_USER_IDS=<id_usuario_1>,<id_usuario_2>

SETTLEMENT_ENABLED=false
```

A URI de redirecionamento deve corresponder à cadastrada no aplicativo OAuth e à configuração do callback local, que utiliza a porta `8000`.

Para o OCR de imagens, configure a autenticação do Google Cloud Vision no ambiente de execução. PDFs com texto nativo não dependem desse serviço.

Para autorizar o acesso ao Tiny pela primeira vez ou reautorizar quando necessário:

```powershell
python -m src.authorize_tiny
```

O navegador será aberto para autorização. Os tokens retornados são armazenados localmente em `data/tiny_tokens.json`, ignorado pelo Git.

O sistema tenta renovar o acesso automaticamente. Caso a autorização seja revogada ou a renovação falhe, será necessária nova autorização manual.

> **Segurança:** os tokens persistidos em arquivo não são criptografados pelo projeto. O acesso ao computador e à pasta de execução deve ser restrito. O arquivo `.env.example` contém somente valores fictícios; `.env` e `data/` estão ignorados pelo Git.

## Modos de operação

### Modo seguro

A interface programática do núcleo é:

```python
main(file_path: str, settlement_enabled: bool = False)
```

O valor padrão permanece `False`, independentemente da configuração do Telegram.

Para executar diretamente:

```python
from src.main import main

result = main(
    file_path="data/input/comprovante_exemplo.pdf",
    settlement_enabled=False,
)

print(result["status"])
print(result["message"])
```

O caminho acima é ilustrativo: substitua-o por um comprovante existente e autorizado.

Em `dry_run`, o sistema **não solicita a baixa financeira**, mas ainda pode consultar a API do Tiny, consumir OCR pago no caso de imagens e registrar informações no SQLite local.

### Configuração de baixa pelo Telegram

O adaptador Telegram utiliza a variável de ambiente `SETTLEMENT_ENABLED`:

| Configuração | Comportamento |
| --- | --- |
| Variável ausente | Modo seguro (`False`) |
| `SETTLEMENT_ENABLED=false` | Conciliação sem solicitar baixa financeira |
| `SETTLEMENT_ENABLED=true` | Permite baixa automática para comprovantes elegíveis, respeitando as validações do núcleo |
| Valor inválido | O bot não inicia até a configuração ser corrigida |

Os valores `true` e `false` são aceitos independentemente de maiúsculas e minúsculas.

**A configuração é carregada na inicialização do bot.** Portanto, alterações no `.env` exigem reiniciar o processo.

A ativação de `SETTLEMENT_ENABLED=true` deve ocorrer somente após homologação e autorização do responsável pela operação financeira.

Uma vez habilitado o modo de produção, os usuários autorizados enviam os comprovantes normalmente. Não é necessária aprovação manual para cada baixa elegível.

**Validação real já realizada:** um comprovante com correspondência única foi processado pelo Telegram com baixa habilitada. A operação retornou `processed` e a baixa foi confirmada diretamente no Tiny. O teste validou o fluxo principal para esse caso, sem representar a homologação final de produção.

## Operação pelo Telegram

Execute a partir da raiz do projeto, após configurar o `.env` e concluir a autorização inicial do Tiny:

```powershell
python -m src.telegram_bot
```

O bot utiliza **long polling**. Mantenha **apenas uma instância** em execução.

O acesso exige simultaneamente:

- O grupo privado configurado em `TELEGRAM_ALLOWED_CHAT_ID`.
- O ID do remetente incluído em `TELEGRAM_ALLOWED_USER_IDS`.

O bot recebe fotos e documentos PDF, JPG, JPEG e PNG. Outros tipos de mensagem não são processados, e instruções nas legendas dos comprovantes não alteram as regras de conciliação.

O adaptador limita o tamanho dos arquivos a **10 MB**, verifica extensão e MIME dos documentos e valida a assinatura inicial após o download.

Os arquivos são armazenados temporariamente e descartados após o processamento. O núcleo é executado em uma thread auxiliar, com bloqueio para processar um comprovante por vez.

### Mensagens operacionais

As respostas utilizam três indicadores visuais:

| Indicador | Significado |
| --- | --- |
| ✅ | Confirmação de processamento ou baixa já registrada |
| ⚠️ | Atenção, modo de teste ou necessidade de conferência |
| ❌ | Resultado negativo ou falha de processamento |

Quando disponíveis, as mensagens apresentam:

- **CPF/CNPJ:** somente números, facilitando copiar e pesquisar no Tiny.
- **Valor:** formato brasileiro, como `R$ 1.179,06`.
- **Data do pagamento:** formato `DD/MM/AAAA`.

Essas informações permitem localizar a conta no ERP sem precisar transcrever manualmente os dados da imagem original.

A resposta também diferencia o resultado financeiro. Por exemplo:

**Baixa confirmada**

```text
✅ Baixa realizada com sucesso no Tiny.

CPF/CNPJ: 12345678000190
Valor: R$ 1.179,06
Data do pagamento: 15/10/2026
```

**Correspondência ambígua**

```text
⚠️ Mais de uma conta correspondente encontrada.
Nenhuma baixa realizada. Confira no Tiny.

CPF/CNPJ: 12345678000190
Valor: R$ 1.179,06
Data do pagamento: 15/10/2026
```

**Transferência Pix não elegível**

```text
⚠️ Transferência via Pix identificada.
Este tipo de comprovante não é elegível para
baixa automática. Confira manualmente no Tiny.
Nenhuma baixa realizada.

Data do pagamento: 13/10/2026
```

As mensagens são adaptadas aos dados efetivamente extraídos. Campos ausentes não são preenchidos artificialmente.

A classificação específica de transferência Pix utiliza o motivo retornado pelo núcleo, sem confundir essa situação com outros casos de revisão manual.

**Importante:** dados obtidos por OCR podem exigir conferência visual. A mensagem facilita a pesquisa, mas não substitui a verificação do comprovante e do lançamento no Tiny quando houver necessidade de intervenção.

### Disponibilidade do bot

O computador responsável pela execução deve permanecer ligado, conectado à internet e com o processo ativo para atendimento contínuo.

Em teste operacional, comprovantes enviados enquanto o bot estava desligado foram processados após sua inicialização. Esse comportamento não representa garantia de recuperação de mensagens em todas as situações.

O MVP não utiliza fila persistente própria, webhook ou múltiplas instâncias.

## Resultados e estados do processamento

A função principal retorna um dicionário com `status`, `message`, `reason`, `transaction_id`, `id_tiny`, `beneficiary_document`, `payment_date` e `amount`.

| Status | Significado |
| --- | --- |
| `dry_run` | Correspondência identificada, sem solicitar baixa financeira |
| `processed` | Baixa confirmada no Tiny e estado local atualizado |
| `already_processed` | Transação já registrada como processada |
| `already_in_review` | Transação anteriormente encaminhada à revisão |
| `review_required` | Comprovante inelegível ou situação que exige conferência manual |
| `no_match` | Nenhuma conta correspondente encontrada |
| `ambiguous_match` | Mais de uma correspondência possível |
| `verification_pending` | Resultado financeiro ou atualização local exige conferência antes de prosseguir |
| `error` | Falha de processamento ou integração identificada |

O campo `reason` permite diferenciar situações que compartilham o mesmo `status`.

Por exemplo, `unsupported_payment_type` identifica a transferência Pix não elegível, enquanto `ineligible_receipt` identifica outros comprovantes que não atendem aos requisitos de automação.

A distinção permite apresentar uma orientação específica no Telegram sem modificar as regras de conciliação.

## Segurança e tratamento de falhas

Os controles financeiros do MVP incluem:

- **Baixa desabilitada por padrão:** `settlement_enabled=False` permanece como comportamento seguro da função principal.
- **Identidade financeira:** hash do arquivo e identificadores de transação ajudam a impedir processamento repetido de um mesmo pagamento.
- **Estados persistidos:** `processing`, `processed` e `review_required` distinguem processamento pendente, concluído e situações que precisam de intervenção.
- **Proteção contra baixa duplicada:** transações pendentes associadas à mesma conta do Tiny são consideradas antes de uma nova tentativa.
- **Confirmação remota:** uma baixa somente é considerada confirmada após nova consulta ao estado da conta no ERP.
- **Falhas inconclusivas:** timeout ou erro após solicitar uma baixa não prova que ela deixou de ocorrer. A recuperação exige verificação, sem repetição automática do POST financeiro.

### Recuperação manual de uma baixa inconclusiva

Se o sistema retornar `verification_pending` ou houver suspeita de interrupção durante uma baixa:

1. **Não repetir a baixa automaticamente** e não reenviar o comprovante esperando uma segunda tentativa financeira.
2. Localizar a conta no Tiny utilizando os dados do comprovante e verificar se o pagamento já foi baixado.
3. Conferir o registro local da transação e os logs com o responsável técnico.
4. Resolver a pendência somente após determinar o estado financeiro real. Se houver dúvida, manter a operação bloqueada para conferência.

A rotina definitiva de resolução de estados locais ainda será validada na homologação do cliente.

### Reinício e manutenção básica

Se o bot parar de responder, verificar se o computador está ligado, conectado à internet e se existe outra instância do processo em execução.

Após corrigir o problema, iniciar novamente:

```powershell
python -m src.telegram_bot
```

Se a autorização do Tiny estiver indisponível, executar novamente:

```powershell
python -m src.authorize_tiny
```

O procedimento de instalação deve identificar o responsável pela execução do bot e pela guarda dos arquivos locais, incluindo banco SQLite, tokens e logs.

Cópias de segurança devem ser realizadas de forma compatível com o uso local do projeto, sem expor credenciais ou dados financeiros.

## Testes e validação

A suíte automatizada utiliza `pytest`. Execute na raiz do repositório:

```powershell
python -m pytest -q
```

**198 testes passaram.**

A suíte cobre componentes como extração de dados, parsing, matching, persistência, integração simulada com o Tiny, regras de elegibilidade, tratamento de estados financeiros, validação de anexos, autorização do Telegram, formatação de mensagens e configuração do modo de baixa.

Também foram realizados testes com comprovantes reais em modo seguro e uma baixa financeira real controlada, confirmada no ERP.

A homologação final deverá validar a instalação no computador do cliente, os usuários autorizados, comprovantes PDF e imagem representativos, reinício do processo, comportamento de reenvio e recuperação manual de situações inconclusivas.

## Estrutura do projeto

```text
payment-reconciliation-automation/
├── src/
│   ├── main.py                     # Orquestração do processamento
│   ├── telegram_bot.py             # Interface operacional Telegram
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
├── .env.example
└── README.pt-br.md
```

A estrutura apresenta os principais componentes, não uma listagem exaustiva. Arquivos de dados, comprovantes, banco SQLite e tokens locais não devem ser versionados.

## Estado atual e próximos passos

O núcleo financeiro, a integração Telegram e a configuração explícita de habilitação de baixas estão implementados.

A prioridade agora é concluir a entrega do MVP, com foco em:

1. Validar os cenários financeiros inconclusivos relevantes, especialmente falhas após uma solicitação de baixa.
2. Finalizar o procedimento simples de recuperação manual de transações pendentes.
3. Revisar a exposição desnecessária de dados financeiros no terminal e nos logs.
4. Instalar e homologar a aplicação no computador do cliente.
5. Confirmar os responsáveis pela operação, reinício, credenciais e cópias de segurança.
6. Habilitar a operação financeira contínua somente após a autorização e o aceite final.

Fila persistente, Redis, Celery, múltiplas instâncias, monitoramento sofisticado, dashboards e novas integrações não são requisitos desta entrega.

Melhorias futuras serão avaliadas a partir de necessidades observadas na operação, priorizando confiabilidade, simplicidade e manutenção.

A eventual publicação deste repositório como case profissional dependerá de revisão de confidencialidade e autorização apropriada. Esta documentação não constitui autorização para executar baixas financeiras em produção.