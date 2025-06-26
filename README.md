# Caça CORS

## Sumário
- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
  - [Detecção de Mãos](#detecao-de-maos)
  - [Contagem de Dedos](#contagem-de-dedos)
  - [Visualização em Tempo Real](#visualizacao-em-tempo-real)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pre-requisitos)
- [Como Configurar e Executar](#como-configurar-e-executar)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Contribuição](#contribuicao)
- [Licença](#licenca)

<br>

## Sobre o Projeto
Este projeto simples em Python utiliza as bibliotecas OpenCV e MediaPipe para detectar e contar o número de dedos levantados em uma mão em tempo real, usando a webcam.

<br>

## Funcionalidades
### Detecção de Mãos: 
Identifica a presença de uma ou duas mãos no quadro da webcam.

### Contagem de Dedos: 
Conta o número de dedos estendidos para cada mão (esquerda e direita) e exibe o total.
O código verifica a posição do topo de cada dedo (pontos 8, 12, 16 e 20) em relação à sua base (pontos 6, 10, 14 e 18, respectivamente). 
Se a ponta do dedo estiver acima da base, ele é considerado levantado. 
O polegar (ponto 4) é tratado de forma diferente, comparando sua posição horizontal.

### Visualização em Tempo Real: 
Desenha os pontos de referência (landmarks) das mãos e exibe os contadores na tela.
Os contadores de dedos para a mão esquerda, direita e o total são exibidos na tela da webcam em tempo real. 
Os pontos de referência das mãos também são desenhados para uma visualização clara.

<br>

## Tecnologias Utilizadas
- Python: Linguagem de programação principal.

- OpenCV: Biblioteca de visão computacional usada para capturar o vídeo da webcam e exibir os resultados.

- MediaPipe: Estrutura de aprendizado de máquina para detecção e rastreamento de mãos.

<br>

## Pré-requisitos
Antes de executar o projeto, certifique-se de ter o Python instalado. Em seguida, instale as bibliotecas necessárias usando o pip:

```bash
pip install opencv-python mediapipe
```

<br>

## Como Configurar e Executar
1. Clone ou baixe este repositório.

2. Navegue até o diretório do projeto.

3. Execute o script Python:

```bash
python main.py
```

4. A janela da sua webcam será aberta, e o programa começará a detectar suas mãos e contar os dedos em tempo real.

<br>

## Arquitetura do Projeto
A estrutura do projeto é simples e organizada da seguinte forma:

```
├── src 
│   └── main.py 
└── README.md
└── LICENSE.md
```

<br>

## Contribuição
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues para bugs ou sugestões de funcionalidades, ou enviar pull requests.

<br>

## Licença
Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE.md](LICENSE.md) para mais detalhes.

Desenvolvido com 💖