
<img width="444" height="465" alt="Captura de pantalla 2026-03-21 230322" src="https://github.com/user-attachments/assets/9ecb0349-eb71-48c6-b4bb-a02364cdc1ca" />

⬡ Espejo MIDI
Espeja tu teclado MIDI en tiempo real — invierte la disposición de notas, ajusta la octava y la corrección de nota. Soporta múltiples controladores simultáneamente.
---
¿Para qué sirve?
Espejo MIDI está diseñado para pianistas que quieren tocar con la mano izquierda usando una digitación simétrica, se puede aplicar a cualquier controlador MIDI y usarlo con el programa que prefieras.
En lugar de que el Do esté a la izquierda y el Si a la derecha, el teclado se invierte: las notas graves quedan a la derecha y las agudas a la izquierda.
---
Características
🎹 Espejo en tiempo real — sin latencia perceptible
🎛️ Corrección de nota — ajusta el desplazamiento en semitonos para que el Do quede en su lugar correcto
🎼 Octavizador — sube o baja hasta 4 octavas
🖥️ Múltiples controladores simultáneos — añade o quita controladores con un botón
💾 Guarda la configuración automáticamente al cerrar
🌙 Tema oscuro y claro — cambia con un botón
📋 Consola de errores integrada
🏷️ Tooltips en todos los botones
✅ Compatible con Windows 10 y Windows 11
---
Requisitos
Python 3.8+
loopMIDI — crea un puerto MIDI virtual en Windows
👉 Descargar loopMIDI
Instalar dependencias
```bash
pip install mido python-rtmidi
```
---
Uso
Opción A — Ejecutar con Python
```bash
python espejo.py
```
Opción B — Ejecutable
Descarga el archivo `EspejoMIDI.exe` desde la sección Releases.
---
Configuración inicial
Abre loopMIDI y crea un puerto virtual (por ejemplo: `EspejoMIDI`)
Abre Espejo MIDI
Selecciona tu controlador en ENTRADA MIDI
Selecciona el puerto de loopMIDI en SALIDA MIDI
Ajusta la corrección de nota si es necesario (valor por defecto: 3)
Pulsa ACTIVAR
En tu DAW o en tu programa preferido, selecciona el puerto de loopMIDI como entrada
```
\[Controlador MIDI] → \[Espejo MIDI] → \[loopMIDI] → \[Ableton / Synthesia / cualquier DAW]
```
---
Corrección de nota
El valor por defecto es 3 y funciona correctamente en la mayoría de controladores. Si al tocar las notas no suenan en la posición correcta, prueba a subir o bajar este valor en pasos de 1 hasta que el Do quede donde corresponde.
El rango útil suele estar entre 0 y 12 semitonos dependiendo del controlador.
---
Compilar a .exe
```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon="espejomidi.ico" --hidden-import=rtmidi --hidden-import=mido.backends.rtmidi --collect-all mido --name "EspejoMIDI" espejo.py
```
El ejecutable se genera en la carpeta `dist/`.
---
Tecnologías
Python
mido — manejo de mensajes MIDI
python-rtmidi — interfaz con los puertos MIDI del sistema
tkinter — interfaz gráfica
loopMIDI — puertos MIDI virtuales en Windows
---
Licencia
MIT — úsalo, modifícalo y compártelo libremente.
---
Desarrollado para pianistas zurdos o para quien quiera experimentar con una nueva forma de tocar.
