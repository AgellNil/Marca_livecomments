# %%
import time
import fire
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, timedelta


def obtener_equipos_desde_url(url):
    # Utiliza una expresión regular para buscar los nombres de los equipos en la URL
    match = re.search(r'/([^/]+)-([^/]+)/\d{4}/\d{2}/\d{2}/', url)
    if match:
        equipo_local, equipo_visitante = match.groups()
        # Reemplaza los guiones con espacios si es necesario
        equipo_local = equipo_local.replace('-r', '')
        if equipo_visitante == "madrid":
            equipo_visitante = "r-madrid"
        else:
            equipo_visitante = equipo_visitante.replace('-', ' ')
        return equipo_local, equipo_visitante
    else:
        return None, None


def scrape_comments_live(url, aux):
    equipo_a, equipo_b = obtener_equipos_desde_url(url)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(5)

    # Aceptar cookies (si es necesario)
    try:
        agree_button = driver.find_element(By.ID, "didomi-notice-agree-button")
        agree_button.click()
        time.sleep(5)
    except:
        pass

    ver_comentarios_button = driver.find_element(By.XPATH, "//button[@title='Ver comentarios']")
    time.sleep(5)

    if ver_comentarios_button:
        ver_comentarios_button.click()

        # Contador para realizar el bucle un máximo de diez veces
        contador = 0

        while contador < 10:
            try:
                mas_comentarios_button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.paginador-button'))
                )
                mas_comentarios_button.click()
                contador += 1
            except:
                break

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    comments = soup.find_all(class_='comentario')
    comments.pop(0)
    comments.pop(0)
    data = []

    for comment in comments:
        num_comment_element = comment.find(class_='numero_comentario').text.strip()
        num_match = re.search(r'#(\d+)', num_comment_element)

        if num_match:
            num_comment = int(num_match.group(1))
            if num_comment > aux:  # Filtrar comentarios con valor mayor que 'aux'
                username_element = comment.find(class_='nombre_usuario')
                if username_element:
                    username = username_element.text.strip()
                else:
                    username = 'No se encontró el nombre de usuario'

                date = comment.find(class_='fecha').text.strip()
                hora = comment.find(class_='hora').text.strip()

                comment_text_element = comment.find_all('p')[1]
                comment_text = comment_text_element.get_text()
                if comment_text.startswith('@'):
                    respon_match = re.search(r'#(\d+)', comment_text)
                    try:
                        respon = respon_match.group(1)
                    except:
                        pass
                    last_newline_position = comment_text.rfind('\n')
                    comment = comment_text[last_newline_position + 1:]
                else:
                    comment = comment_text
                    respon = None

                data.append([equipo_a, equipo_b, username, num_comment, date, hora, comment, respon])

    driver.quit()
    df = pd.DataFrame(data, columns=['equip_l', 'equip_v', 'nom_usuari', 'num_comment', 'data', 'hora', 'comment',
                                     'num_referencia'])
    return df


# %%

def create_comment_dataframe_with_timeout(url):
    comentarios = pd.DataFrame(
        columns=['equip_l', 'equip_v', 'nom_usuari', 'num_comment', 'data', 'hora', 'comment', 'num_referencia'])
    aux = 0
    start_time = datetime.now()  # Registra la hora de inicio

    try:
        while True:
            current_time = datetime.now()

            # Verifica si han pasado más de 7 horas desde el inicio
            if current_time - start_time >= timedelta(hours=7):
                print("Se han pasado 6 horas. Finalizando la extracción de comentarios.")
                break

            nuevos_comentarios = scrape_comments_live(url, aux)
            comentarios = pd.concat([comentarios, nuevos_comentarios], ignore_index=True)
            aux = max(comentarios['num_comment'])
            print(aux)

            # Espera 1 minuto antes de la próxima llamada
            time.sleep(5)  # Sleep for 60 seconds (1 minute)

    except KeyboardInterrupt:
        # Manejar la interrupción del usuario (Ctrl+C)
        pass

    return comentarios


def main(input_url, output_file):
    # Ejemplo de uso, donde 'URL_DEL_PARTIDO' es la URL real del partido
    df = create_comment_dataframe_with_timeout(input_url)
    # %%
    df.to_csv('barcamadrid.csv')
    # %%

if __name__ == '__main__':
    #main('https://www.marca.com/futbol/primera-division/barcelona-vs-real-madrid/cronica/2021/10/24/6175b1a3e2704e8b6d8b45c8.html', 'barcamadrid.csv')
    fire.Fire(main)