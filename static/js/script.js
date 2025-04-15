// static/js/script.js
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const uploadForm = document.getElementById('upload-form');
const submitButton = document.getElementById('submit-button');
const statusDiv = document.getElementById('status');

let selectedFiles = []; // Array zum Speichern der File-Objekte

const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff', 'application/pdf'];
const allowedExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.pdf'];

// --- Drag & Drop Event Listener ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', async (e) => { // async machen!
    e.preventDefault();
    dropZone.classList.remove('dragover');
    setStatus('Verarbeite Drag & Drop...', 'info');

    const items = e.dataTransfer.items;
    let filesToAdd = []; // Temporäre Liste für neue Dateien

    // Funktion, um rekursiv durch Ordner zu gehen
    async function scanDirectory(entry) {
        return new Promise((resolve, reject) => {
            if (entry.isDirectory) {
                console.log(`Scanning directory: ${entry.name}`);
                const reader = entry.createReader();
                reader.readEntries(async (entries) => {
                    // Promise.all, um auf alle Unterordner/Dateien zu warten
                    await Promise.all(entries.map(async (innerEntry) => {
                        await scanDirectory(innerEntry); // Rekursiver Aufruf
                    }));
                    resolve(); // Fertig mit diesem Verzeichnislevel
                }, reject); // Fehler beim Lesen des Verzeichnisses
            } else if (entry.isFile) {
                entry.file(file => { // File-Objekt holen
                    // Prüfen, ob der Dateityp oder die Endung erlaubt ist
                    const lowerCaseName = file.name.toLowerCase();
                    const extensionMatch = allowedExtensions.some(ext => lowerCaseName.endsWith(ext));
                    // Manchmal ist der Typ nicht verfügbar, daher auch Endung prüfen
                    if (allowedTypes.includes(file.type) || (file.type === "" && extensionMatch)) {
                         // Doppelte Einträge vermeiden (prüft Name und Größe)
                        if (!selectedFiles.some(existing => existing.name === file.name && existing.size === file.size) &&
                            !filesToAdd.some(adding => adding.name === file.name && adding.size === file.size)) {
                            filesToAdd.push(file);
                            console.log(`Datei hinzugefügt: ${file.name}`);
                        } else {
                             console.log(`Datei übersprungen (bereits vorhanden): ${file.name}`);
                        }
                    } else {
                         console.log(`Datei übersprungen (Typ nicht erlaubt): ${file.name}`);
                    }
                    resolve(); // Fertig mit dieser Datei
                }, reject); // Fehler beim Holen des File-Objekts
            } else {
                 resolve(); // Eintrag ist weder Datei noch Ordner
            }
        });
    }

    // Starte das Scannen für jedes Top-Level-Item
    try {
        if (items && items.length > 0) {
            // Warten, bis alle Einträge (Dateien und Ordner) verarbeitet wurden
            await Promise.all(Array.from(items).map(item => {
                const entry = item.webkitGetAsEntry();
                if (entry) {
                    return scanDirectory(entry);
                }
                return Promise.resolve(); // Ignoriere Items, die keine Einträge sind
            }));
        }

        // Füge die gesammelten Dateien zur Hauptliste hinzu
        selectedFiles.push(...filesToAdd);
        updateFileList();
        updateSubmitButton();
        setStatus(filesToAdd.length > 0 ? `${filesToAdd.length} Datei(en) hinzugefügt.` : 'Keine neuen gültigen Dateien gefunden.', 'info');

    } catch (error) {
        console.error("Fehler beim Verarbeiten der Ordner/Dateien:", error);
        setStatus('Fehler beim Lesen der Ordnerstruktur.', 'error');
    }
});


// --- File Input Event Listener (bleibt gleich, behandelt nur einzelne Dateien) ---
fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    handleFiles(files); // Bestehende Funktion wiederverwenden
});

// --- Bestehende Datei-Handler-Funktion (jetzt primär für File-Input) ---
function handleFiles(files) {
    statusDiv.textContent = '';
    statusDiv.className = '';
    let countAdded = 0;

    Array.from(files).forEach(file => {
        const lowerCaseName = file.name.toLowerCase();
        const extensionMatch = allowedExtensions.some(ext => lowerCaseName.endsWith(ext));
        if (allowedTypes.includes(file.type) || (file.type === "" && extensionMatch)) {
            if (!selectedFiles.some(existingFile => existingFile.name === file.name && existingFile.size === file.size)) {
                selectedFiles.push(file);
                countAdded++;
            }
        }
    });

    updateFileList();
    updateSubmitButton();
     if (countAdded > 0) {
        setStatus(`${countAdded} Datei(en) hinzugefügt.`, 'info');
    }
}

// --- Restliche Funktionen (updateFileList, removeFile, updateSubmitButton, uploadForm submit, setStatus) bleiben weitgehend gleich ---
// Kleine Anpassung in updateFileList für bessere Lesbarkeit
function updateFileList() {
    fileList.innerHTML = '';
    if (selectedFiles.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'Keine Dateien ausgewählt.';
        li.style.color = '#888';
        fileList.appendChild(li);
    } else {
        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            const removeBtn = document.createElement('button');
            removeBtn.textContent = 'x';
            removeBtn.title = 'Datei entfernen';
            removeBtn.style.marginLeft = '10px';
            removeBtn.style.cursor = 'pointer';
            removeBtn.style.border = 'none';
            removeBtn.style.background = 'none';
            removeBtn.style.color = 'red';
            removeBtn.style.fontWeight = 'bold';
            removeBtn.onclick = (e) => {
                e.stopPropagation(); // Verhindert andere Klick-Events
                removeFile(index);
            };
            li.appendChild(removeBtn);
            fileList.appendChild(li);
        });
    }
}

function removeFile(index) {
    console.log(`Entferne Datei: ${selectedFiles[index].name}`);
    selectedFiles.splice(index, 1);
    updateFileList();
    updateSubmitButton();
}


function updateSubmitButton() {
    submitButton.disabled = selectedFiles.length === 0;
}

// uploadForm Event Listener (Submit) bleibt unverändert

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (selectedFiles.length === 0) {
        setStatus('Bitte wählen Sie zuerst Dateien aus.', 'error');
        return;
    }

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file); // 'files' muss mit dem Backend übereinstimmen
    });

    setStatus(`Sende ${selectedFiles.length} Datei(en) zur Verarbeitung...`, 'info');
    submitButton.disabled = true;

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            const disposition = response.headers.get('Content-Disposition');
            let filename = 'presentation.pptx';
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) {
                  filename = matches[1].replace(/['"]/g, '');
                }
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();
            setStatus('PPTX erfolgreich erstellt und heruntergeladen!', 'success');
            // Dateiliste und Auswahl leeren nach Erfolg
            selectedFiles = [];
            fileInput.value = null; // Wichtig, damit gleiche Datei erneut gewählt werden kann
            updateFileList();

        } else {
            const errorData = await response.json();
            console.error("Serverfehler:", errorData);
            setStatus(`Fehler vom Server: ${errorData.error || response.statusText}`, 'error');
        }
    } catch (error) {
        console.error('Fetch oder Verarbeitungsfehler:', error);
        setStatus('Ein Netzwerk- oder Client-Fehler ist aufgetreten. Prüfen Sie die Konsole.', 'error');
    } finally {
        updateSubmitButton(); // Button-Status aktualisieren (könnte noch deaktiviert sein, wenn Liste leer)
    }
});

function setStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = type;
}

// Initialer Zustand
updateSubmitButton();
updateFileList(); // Zeigt "Keine Dateien ausgewählt" initial an
