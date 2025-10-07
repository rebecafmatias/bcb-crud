FROM astrocrpublic.azurecr.io/runtime:3.1-1

# Copia e instala dependências do projeto
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
