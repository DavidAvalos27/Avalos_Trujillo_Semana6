# Tres en Raya Invencible con Minimax, Poda Alfa-Beta y OpenCV

Proyecto de Inteligencia Artificial desarrollado en Python.

## Objetivo

Construir un juego de Tres en Raya matematicamente invencible. La IA usa Minimax optimizado con Poda Alfa-Beta y el turno humano se habilita automaticamente cuando OpenCV detecta un rostro frente a la camara.

## Caracteristicas

- IA invencible con Minimax y poda Alfa-Beta.
- Evaluacion con profundidad para preferir victorias rapidas y retrasar derrotas inevitables.
- Interfaz web HTML moderna, clara, roja e interactiva con Flask.
- Version de escritorio opcional con Tkinter.
- Reconocimiento facial con OpenCV usando Haar Cascades y video en vivo.
- Bloqueo del turno humano si no hay rostro detectado.
- Selector de inicio: humano o IA.
- Tres modos: facil, normal e imposible.
- Codigo organizado por capas: motor logico, vision, interfaz y pruebas.

## Estructura

```text
Avalos_Trujillo_Sem5/
  run.py
  run_desktop.py
  requirements.txt
  src/
    main.py
    game/
      board.py
      minimax.py
    web/
      app.py
      templates/
        index.html
      static/
        styles.css
        app.js
    ui/
      app.py
    vision/
      face_detector.py
  tests/
    test_minimax.py
```

## Instalacion

Desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecucion

Version web HTML recomendada para la presentacion:

```powershell
python run.py
```

Luego abre:

```text
http://127.0.0.1:5000
```

Version de escritorio alternativa:

```powershell
python run_desktop.py
```

Si OpenCV no puede abrir la camara, el programa muestra el estado correspondiente. Para cumplir la practica, ejecutalo en una laptop o PC con camara activa.

## Pruebas

```powershell
python -m unittest discover -s tests
```

## Como se cumple la invencibilidad

El algoritmo analiza todos los futuros estados posibles del tablero. La IA maximiza su puntaje y asume que el humano tambien jugara de forma optima. Con la Poda Alfa-Beta se evitan ramas que no pueden mejorar el resultado final, reduciendo nodos explorados sin cambiar la decision optima.

Puntajes:

- Victoria de IA: `10 - profundidad`
- Victoria humana: `profundidad - 10`
- Empate: `0`

Esto hace que la IA gane lo antes posible, empate cuando no puede ganar y nunca elija una linea perdedora si existe una opcion mejor.

## Modos de juego

- Facil: la IA juega de forma aleatoria.
- Normal: la IA bloquea amenazas y a veces usa Minimax.
- Imposible: usa Minimax con Poda Alfa-Beta. Esta configurado para preferir empates cuando existe una linea de empate, por lo que el resultado esperado contra un humano cuidadoso es empate.

## Entregable en GitHub

1. Crea un repositorio nuevo en GitHub.
2. Sube todo el contenido de esta carpeta.
3. En la descripcion del repositorio indica: `Tres en Raya con Minimax, Poda Alfa-Beta y OpenCV`.
4. Graba un video corto mostrando: deteccion de rostro, seleccion de modo, seleccion de quien inicia y una partida en modo imposible.
