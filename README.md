# 🎓 English Tutor AI

<div align="center">
  <p>Um tutor de inglês inteligente que ajuda estudantes a melhorar suas habilidades de escrita e fala em inglês com feedback personalizado.</p>
  
  [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
  [![OpenAI](https://img.shields.io/badge/OpenAI-API-412991.svg)](https://openai.com/)
  [![Gradio](https://img.shields.io/badge/Gradio-UI-FF4B4B.svg)](https://gradio.app/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
</div>

## ✨ Funcionalidades

- **Avaliação de Escrita**: Receba feedback detalhado sobre sua redação em inglês
- **Correção Gramatical**: Identificação e correção de erros gramaticais
- **Avaliação por Nível**: Feedback personalizado baseado no seu nível de inglês (1-10)
- **Interface Intuitiva**: Fácil de usar com suporte a gravação de áudio
- **Feedback Construtivo**: Dicas práticas para melhorar cada aspecto do seu inglês
- **Respostas em streaming**: visualize o texto sendo gerado em tempo real

## 🛠️ Tecnologias

- **Python 3.8+** - Linguagem principal
- **OpenAI API** - Para processamento de linguagem natural e transcrição de áudio
- **Gradio** - Interface web interativa
- **Pydub** - Processamento de áudio
- **Poetry** - Gerenciamento de dependências

## 🚀 Como Começar

### Pré-requisitos

- Python 3.8 ou superior
- Conta na [OpenAI](https://openai.com/) (para obter uma chave de API)
- [Poetry](https://python-poetry.org/) instalado (recomendado)

### Configuração

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/english-tutor-ai.git
   cd english-tutor-ai
   ```

2. Crie e ative o ambiente virtual:
   ```bash
   poetry install
   poetry shell
   ```

3. Configure suas variáveis de ambiente:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env com suas credenciais
   ```

4. Execute a aplicação:
   ```bash
   python main.py
   ```

5. Acesse a interface no navegador:
   ```
   http://localhost:7860
   ```

## 🏗️ Estrutura do Projeto

```
English-Tutor-AI/
├── data/                  # Dados e recursos
├── src/
│   ├── core/             # Lógica principal da aplicação
│   ├── services/          # Serviços externos (OpenAI, etc.)
│   ├── models/           # Modelos de dados e prompts
│   └── utils/             # Utilitários e funções auxiliares
├── tests/                 # Testes automatizados
├── .env.example          # Exemplo de variáveis de ambiente
├── environment.yml       # Configuração do ambiente Conda
├── main.py               # Ponto de entrada da aplicação
└── pyproject.toml        # Dependências do Poetry
```

## 📝 Como Usar

1. **Modo Escrita**:
   - Selecione seu nível de inglês (1-10)
   - Digite ou cole seu texto em inglês
   - Receba feedback detalhado e uma nota de 0 a 10

2. **Modo Fala**:
   - Grave um áudio com sua fala em inglês
   - Receba transcrição e feedback de pronúncia

## 🤝 Contribuição

Contribuições são bem-vindas! Siga estes passos:

1. Dê Fork no projeto
2. Crie uma Branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## 📧 Contato

Seu Nome - [@seu_twitter](https://twitter.com/seu_twitter) - seu.email@exemplo.com

Link do Projeto: [https://github.com/seu-usuario/english-tutor-ai](https://github.com/seu-usuario/english-tutor-ai)

## 🙏 Agradecimentos

- [OpenAI](https://openai.com/) por fornecer a API incrível
- A todos os contribuidores que ajudaram a melhorar este projeto
- A comunidade de código aberto por todo o suporte
