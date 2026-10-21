# Automação de Conciliação de Pagamentos

🌐 **Read this in [English](https://github.com/vagner-lcf/payment-reconciliation-automation/blob/master/README.md).**

Projeto em Python desenvolvido a partir de uma necessidade operacional real: conferir comprovantes de pagamento, localizar os lançamentos correspondentes no contas a pagar do Tiny/Olist ERP e, quando autorizado, realizar a baixa financeira de forma controlada.

A solução integra extração de dados de comprovantes, regras determinísticas de conciliação, API do Tiny/Olist ERP e persistência local para reduzir conferências repetitivas e controlar o risco de processamento duplicado.

> **Estado atual — 21/10/2026:** núcleo financeiro e integração Telegram implementados, com **198 testes automatizados aprovados**. O programa passou por uma validação funcional com um lote de 62 comprovantes reais, incluindo baixas confirmadas no Tiny. A inicialização automática no Windows e a proteção contra múltiplas instâncias também foram testadas localmente. **A instalação e a homologação operacional no computador da cliente permanecem pendentes.**

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
- **Respostas operacionais:** mensagens com indicadores visuais, CPF/CNPJ, valor, data do pagamento e referência local da transação, quando disponíveis, facilitando a conferência manual no Tiny.
- **Modo de operação configurável:** habilitação ou desabilitação de baixas financeiras pelo Telegram por meio da variável `SETTLEMENT_ENABLED`.
- **Inicialização no Windows:** execução por arquivo `.bat`, com controlador PowerShell e atalhos.
- **Proteção contra múltiplas instâncias:** bloqueio exclusivo de arquivo para impedir duas execuções simultâneas iniciadas pelo mecanismo Windows.
- **Inicialização automática após login:** execução por atalho na pasta de Inicialização do Windows, validada em ambiente local.

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

### Inicialização no Windows

Na implantação local Windows, o fluxo de execução é:

```text
Atalho do Windows
       |
       v
scripts/windows/start_bot.bat
       |
       v
scripts/windows/run_bot.ps1
       |
       +--> Bloqueio exclusivo indisponível
       |           |
       |           v
       |      Alerta de instância existente
       |
       v
Bloqueio exclusivo adquirido
       |
       v
.venv/Scripts/python.exe -m src.telegram_bot
       |
       v
Bot Telegram em execução
```

O mecanismo de inicialização não modifica as regras financeiras do núcleo.

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
| Windows Batch + PowerShell | Inicialização, controle de instância e operação local |

As decisões de correspondência e elegibilidade são implementadas por **regras explícitas**, não por um modelo de IA que decide autonomamente se uma conta deve ser baixada.

## Instalação e configuração

**Pré-requisitos:** Python compatível com as dependências de `requirements.txt`, acesso autorizado à API v3 do Tiny/Olist ERP e, para processar imagens, credenciais válidas do Google Cloud Vision.

Clone o repositório:

```bash
git clone https://github.com/vagner-lcf/payment-reconciliation-automation.git
cd payment-reconciliation-automation
```

Crie um ambiente virtual no Windows (PowerShell) e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O uso direto do executável do ambiente virtual dispensa sua ativação manual.

Se preferir ativá-lo:

```powershell
.\.venv\Scripts\Activate.ps1
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
.\.venv\Scripts\python.exe -m src.authorize_tiny
```

O navegador será aberto para autorização. Os tokens retornados são armazenados localmente em `data/tiny_tokens.json`, ignorado pelo Git.

O sistema tenta renovar o acesso automaticamente. Caso a autorização seja revogada ou a renovação falhe, será necessária nova autorização manual.

> **Segurança:** os tokens persistidos em arquivo não são criptografados pelo projeto. O acesso ao computador e à pasta de execução deve ser restrito. O arquivo `.env.example` contém somente valores fictícios; `.env` e `data/` estão ignorados pelo Git.

### Configuração do Google Cloud Vision

A autenticação deve ser configurada no computador que executará o programa.

Na implantação no ambiente da cliente, será necessário:

- Configurar o acesso ao Google Cloud Vision em um projeto sob responsabilidade da operação.
- Validar as credenciais disponíveis para o processo Python.
- Confirmar o funcionamento do OCR após um novo login no Windows.
- Acompanhar o consumo da API e configurar alertas de orçamento.
- Restringir o acesso às credenciais e evitar seu compartilhamento por mensagens.

A autenticação já foi testada no ambiente local de desenvolvimento. **A configuração definitiva no computador da cliente ainda não foi realizada.**

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

**Validação real já realizada:** o fluxo de baixa automática foi exercitado com comprovantes reais e baixas confirmadas no ERP. Isso valida os cenários observados, mas não substitui a homologação no computador da cliente.

## Operação pelo Telegram

Execute a partir da raiz do projeto, após configurar o `.env` e concluir a autorização inicial do Tiny:

```powershell
.\.venv\Scripts\python.exe -m src.telegram_bot
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
- **Referência:** identificador local da transação, útil para localizar seu registro e relacioná-lo aos logs.

A referência é um identificador do banco local, **não o número da conta no Tiny**. Ela aparece somente quando a operação possui um identificador de transação disponível.

Essas informações permitem localizar a conta no ERP sem precisar transcrever manualmente os dados da imagem original.

A resposta também diferencia o resultado financeiro. Por exemplo:

**Baixa confirmada**

```text
✅ Baixa realizada com sucesso no Tiny.

CPF/CNPJ: 12345678000190
Valor: R$ 1.179,06
Data do pagamento: 15/10/2026
Referência: 21
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

## Inicialização e operação no Windows

Para a implantação em um computador Windows, foram criados arquivos de inicialização que permitem executar o programa sem abrir o VS Code ou digitar comandos Python.

### Arquivos utilizados

```text
scripts/
└── windows/
    ├── start_bot.bat
    └── run_bot.ps1
```

O `start_bot.bat` apresenta o cabeçalho do programa e orientações operacionais.

O `run_bot.ps1` gerencia o bloqueio de execução única e inicia o ambiente Python do projeto.

A inicialização utiliza o executável:

```text
.venv\Scripts\python.exe
```

com o módulo:

```text
src.telegram_bot
```

### Proteção contra múltiplas instâncias

O controlador PowerShell utiliza um arquivo chamado `bot.lock`, localizado na raiz do projeto.

Ao iniciar, ele tenta abrir esse arquivo com acesso exclusivo.

- **Primeira execução:** o bloqueio é adquirido e o bot é iniciado.
- **Segunda execução:** a tentativa de adquirir o bloqueio falha, e uma mensagem de alerta informa que o programa já está em execução.
- **Encerramento:** o bloqueio é liberado quando o controlador fecha o arquivo ou seu processo termina.

O arquivo `bot.lock` pode permanecer no disco após o encerramento. Sua existência, isoladamente, não significa que o programa esteja funcionando.

Esse arquivo é ignorado pelo Git por representar um artefato local de execução.

**Limitação:** a proteção vale para as instâncias iniciadas pelo controlador `run_bot.ps1`. A execução direta do módulo Python não utiliza esse bloqueio e deve ser evitada quando o bot já estiver ativo.

### Atalho na área de trabalho

É possível criar um atalho do Windows apontando para:

```text
scripts\windows\start_bot.bat
```

O ícone personalizado do projeto fica em:

```text
assets\payment_reconciliation.ico
```

O atalho pode receber o nome **Payment Reconciliation Automation**.

Se o bot já estiver funcionando, abrir esse atalho exibirá o alerta colorido de instância existente, sem iniciar outra execução pelo controlador.

**O atalho inicia o programa; ele não reinicia um processo já ativo.**

### Inicialização automática

A inicialização automática foi configurada e validada utilizando a pasta de Inicialização do Windows:

1. Pressione `Win + R`.
2. Digite `shell:startup`.
3. Crie um atalho para `scripts\windows\start_bot.bat`.
4. Saia da conta do Windows e entre novamente.

Após o login, o Windows executará o atalho e abrirá o bot.

No teste local, a inicialização automática funcionou e o programa respondeu corretamente a um novo comprovante enviado pelo Telegram.

**Limitação importante:** o programa não inicia enquanto o Windows permanece na tela de login. Após um reinício do computador, será necessário entrar na conta para que o atalho de Inicialização seja executado.

Também é necessário garantir que o computador não entre em suspensão durante o período em que o bot deve ficar disponível.

### Encerramento do programa

Para encerrar o bot:

1. Aguarde a resposta ao último comprovante enviado.
2. Confirme que não há processamento em andamento.
3. Na janela do programa, pressione `Ctrl+C`.
4. Se o Windows apresentar a pergunta `Deseja finalizar o arquivo em lotes (S/N)?`, digite `S` e pressione Enter.

Fechar a janela pelo botão `X` também pode encerrar o processo, mas deve ser evitado durante uma operação financeira.

O encerramento durante uma solicitação de baixa pode deixar o resultado inconclusivo, exigindo conferência no Tiny antes de qualquer nova tentativa.

### Reinício manual

Ainda não existe um comando automatizado de reinicialização segura.

O procedimento atual é:

1. Aguardar o término de qualquer comprovante em processamento.
2. Encerrar o programa conforme as orientações anteriores.
3. Abrir novamente o atalho **Payment Reconciliation Automation**.

Esse procedimento evita introduzir um reinício forçado que possa interromper operações financeiras.

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
- **Controle de acesso no Telegram:** somente mensagens do grupo e dos remetentes autorizados são processadas.
- **Execução única no inicializador Windows:** tentativas de iniciar outra instância pelo mesmo controlador são bloqueadas.

O controle de instância do Windows é uma medida operacional adicional. Ele não substitui os mecanismos de idempotência do núcleo financeiro.

### Recuperação manual de uma baixa inconclusiva

Se o sistema retornar `verification_pending` ou houver suspeita de interrupção durante uma baixa:

1. **Não repetir a baixa automaticamente** e não reenviar o comprovante esperando uma segunda tentativa financeira.
2. Localizar a conta no Tiny utilizando os dados do comprovante e verificar se o pagamento já foi baixado.
3. Conferir o registro local da transação e os logs com o responsável técnico.
4. Resolver a pendência somente após determinar o estado financeiro real. Se houver dúvida, manter a operação bloqueada para conferência.

A rotina definitiva de resolução de estados locais ainda deverá ser validada na homologação operacional da cliente.

### Manutenção básica

Se o bot parar de responder, verificar:

- Se o computador está ligado, com usuário conectado e sem suspensão.
- Se existe conexão com a internet.
- Se a janela do programa permanece aberta.
- Se as credenciais do Telegram, Tiny e Google Cloud estão válidas.
- Se os logs apresentam algum erro relevante.

Após resolver o problema, iniciar novamente pelo atalho do Windows.

Se a autorização do Tiny estiver indisponível, executar novamente, na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m src.authorize_tiny
```

O procedimento de instalação deve identificar o responsável pela execução do bot e pela guarda dos arquivos locais, incluindo banco SQLite, tokens e logs.

Cópias de segurança devem ser realizadas de forma compatível com o uso local do projeto, sem expor credenciais ou dados financeiros.

### Atualização do programa

Antes de atualizar o código:

1. Aguardar o encerramento dos processamentos.
2. Encerrar o bot.
3. Realizar backup dos dados locais relevantes, especialmente o banco SQLite.
4. Preservar `.env`, tokens e configurações locais.
5. Atualizar os arquivos do projeto.
6. Instalar eventuais dependências atualizadas.
7. Executar os testes automatizados.
8. Reiniciar o programa e validar seu funcionamento.

**Não excluir a pasta `data/` durante atualizações sem verificar e preservar os arquivos necessários à operação.**

O ambiente virtual `.venv` deve ser criado ou configurado no computador de destino, pois não faz parte do repositório.

## Testes e validação

A suíte automatizada utiliza `pytest`. Execute na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**198 testes passaram na validação local mais recente.**

A suíte cobre componentes como extração de dados, parsing, matching, persistência, integração simulada com o Tiny, regras de elegibilidade, tratamento de estados financeiros, validação de anexos, autorização do Telegram, formatação de mensagens e configuração do modo de baixa.

### Homologação funcional com comprovantes reais

Além dos testes automatizados, foi realizado um lote de validação com **62 comprovantes históricos reais**.

Os resultados registrados foram:

| Resultado | Quantidade |
| --- | ---: |
| Novas baixas realizadas | 14 |
| Comprovantes já processados | 8 |
| Sem correspondência no ERP | 24 |
| Já registrados para revisão | 7 |
| Novos casos de revisão manual | 4 |
| Transferências Pix não elegíveis | 4 |
| Erro com necessidade de nova verificação ou tentativa controlada | 1 |
| **Total** | **62** |

Os resultados demonstraram o funcionamento das regras de conciliação dentro do escopo implementado.

Entretanto, **não é tecnicamente correto calcular uma taxa geral de automação a partir desse lote**, porque parte dos comprovantes históricos não possuía contas correspondentes previamente cadastradas no Tiny.

A ausência de uma conta no ERP impede a baixa automática mesmo quando o comprovante foi interpretado corretamente.

A validação funcional não substitui a conferência final das baixas no ERP nem a homologação no ambiente definitivo da cliente.

### Testes operacionais no Windows

Também foram validados localmente:

- Inicialização do bot pelo arquivo `start_bot.bat`.
- Execução do Python pelo controlador `run_bot.ps1`.
- Bloqueio de uma segunda instância iniciada pelo mesmo mecanismo.
- Exibição do alerta visual de duplicidade.
- Encerramento manual com `Ctrl+C`.
- Inicialização automática após login no Windows.
- Recebimento e resposta a um comprovante após a inicialização automática.

A instalação no computador dedicado da cliente ainda está pendente.

## Estrutura do projeto

```text
payment-reconciliation-automation/
├── assets/
│   └── payment_reconciliation.ico    # Ícone do atalho Windows
├── scripts/
│   └── windows/
│       ├── start_bot.bat             # Inicializador com cabeçalho
│       └── run_bot.ps1               # Controle de instância e execução
├── src/
│   ├── main.py                       # Orquestração do processamento
│   ├── telegram_bot.py               # Interface operacional Telegram
│   ├── receipt_parser.py             # Extração estruturada dos dados
│   ├── pdf_text_extractor.py         # Leitura de PDF
│   ├── image_text_extractor.py       # OCR de imagens
│   ├── receipt_hash_extractor.py     # Identificação por hash
│   ├── matching.py                   # Regras de correspondência
│   ├── tiny_client.py                # Integração com a API do ERP
│   ├── auth.py                       # Fluxos OAuth
│   ├── authorize_tiny.py             # Autorização manual
│   ├── callback.py                   # Callback OAuth local
│   ├── token_manager.py              # Renovação dos tokens
│   ├── token_store.py                # Persistência dos tokens
│   └── tratoray_transactions_db.py   # Persistência das transações
├── tests/                            # Testes automatizados
├── data/                             # Dados locais (ignorados pelo Git)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md                         # Documentação em inglês
└── README.pt-br.md                   # Documentação em português
```

A estrutura apresenta os principais componentes, não uma listagem exaustiva. Arquivos de dados, comprovantes, banco SQLite e tokens locais não devem ser versionados.

O arquivo `bot.lock`, gerado durante a execução pelo controlador Windows, também é ignorado pelo Git.

## Estado atual e próximos passos

O núcleo financeiro, a integração Telegram e a configuração explícita de habilitação de baixas estão implementados.

A validação funcional com comprovantes reais e a preparação da inicialização no Windows foram realizadas.

A prioridade agora é concluir a entrega do MVP, com foco em:

1. Instalar o programa no computador dedicado da cliente.
2. Configurar o ambiente Python e as credenciais do Tiny/Olist ERP, Telegram e Google Cloud Vision.
3. Confirmar a inicialização automática e o funcionamento após novo login no Windows.
4. Conferir amostras das baixas realizadas diretamente no Tiny.
5. Validar a orientação operacional para casos inconclusivos e revisão manual.
6. Definir as responsabilidades por operação, atualização, credenciais e cópias de segurança.
7. Obter a homologação operacional e o aceite final da cliente.

Fila persistente, Redis, Celery, múltiplas instâncias, monitoramento sofisticado, dashboards e novas integrações não são requisitos desta entrega.

Melhorias futuras serão avaliadas a partir de necessidades observadas na operação, priorizando confiabilidade, simplicidade e manutenção.

A eventual publicação deste repositório como case profissional dependerá de revisão de confidencialidade e autorização apropriada. Esta documentação não constitui autorização para executar baixas financeiras em produção.

---

**Desenvolvido por Vagner Fonseca.**

**Repositório:** https://github.com/vagner-lcf/payment-reconciliation-automation
