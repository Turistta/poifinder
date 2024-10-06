# Microsserviço de Seleção de POIs

## Introdução

POIFinder é um microsserviço projetado para recomendar Pontos de Interesse (POIs) aos usuários com base num conjunto de preferências de atividades e hobbies. O sistema utiliza dados de localização, preferências e informações contextuais para fornecer recomendações personalizadas de POIs.

## Funcionalidades/Propósito

O principal propósito do POIFinder é:

1. Ingerir dados do usuário (hobbies, atividades e localização) em um formato pré-definido.
2. Descobrir pontos de interesse na localidade do usuário.
3. Filtrar e selecionar POIs com base nos atributos do usuário (filtragem baseada em conteúdo).
4. Retornar uma lista de POIs filtrados.

## Tecnologias Escolhidas

O POIFinder utiliza uma combinação de tecnologias modernas para oferecer um serviço eficiente e escalável:

- **FastAPI**: Um framework web moderno e rápido para construir APIs com Python, oferecendo alto desempenho e facilidade de uso.
- **Apache Airflow**: Uma plataforma de orquestração de fluxos de trabalho que permite agendar e gerenciar complexos pipelines de dados.

Estas tecnologias foram escolhidas por sua capacidade de lidar com processamento e orquestração de fluxos de trabalho complexos.

## Pré-requisitos

Para executar o POIFinder, você precisará ter instalado:

- Docker e Docker Compose
- Python 3.12 ou superior
- pip (gerenciador de pacotes Python)

## Instalação, Execução e Limpeza

1. Clone o repositório:
   ```
   git clone https://github.com/Turistta/poifinder.git
   cd POIFinder
   ```

2. Configure as variáveis de ambiente:
   - Copie o arquivo `.env_sample` para `.env`, `.app.env`, e `.airflow.env`.
   - Preencha as variáveis de ambiente necessárias em cada arquivo.

3. Construa e inicie os contêineres Docker:
   ```
   cd src
   docker-compose up --build
   ```

4. O serviço FastAPI estará disponível em `http://localhost:3000`.

5. Para acessar a interface do Airflow:
   - Abra `http://localhost:8080` no navegador
   - Use as credenciais configuradas no arquivo `.airflow.env`

6. Para encerrar o serviço:
   ```
   docker-compose down
   ```

7. Para limpar completamente o ambiente (remove volumes, redes e imagens não utilizadas):
   ```
   docker-compose down -v --remove-orphans
   ```

Lembre-se de substituir `<username>`, `<database>`, e `<dag_id>` pelos valores apropriados configurados em seu ambiente.

Estas instruções ajudarão os usuários a gerenciar o ciclo de vida completo do POIFinder, desde a inicialização até o encerramento e limpeza do ambiente. É importante incluir essas informações para garantir que os usuários possam gerenciar eficientemente os recursos e manter um ambiente limpo e organizado.

## Utilização da API

O POIFinder expõe suas funcionalidades através da API FastAPI na porta 3000. Esta API serve como ponto de entrada para o sistema e é responsável por disparar os fluxos de trabalho do Airflow. Aqui estão os principais endpoints:

1. **Buscar POIs**:
   - Endpoint: `POST /pois`
   - Este endpoint recebe os dados do usuário (localização, preferências) e inicia o processo de busca de POIs.
   - Ele dispara a DAG correspondente no Airflow para processar a solicitação.

2. **Status da Busca**:
   - Endpoint: `GET /job/{task_id}`
   - Permite verificar o status de uma tarefa de busca de POIs em andamento.

3. **Resultados da Busca**:
   - Endpoint: `GET /results/{task_id}`
   - Retorna os resultados de uma busca de POIs concluída.

Para mais detalhes em como utilizar o serviço, consulte a documentação em `http://localhost:3000/docs`
