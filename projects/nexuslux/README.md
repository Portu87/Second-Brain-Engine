# Proyecto NexusLux

Esta instancia se rige por el modelo de autoridad compilada de Second Brain Engine.

## Autoridad vigente

- Decisión aprobada: `DEC-NEXUSLUX-CONSTITUTION-V1-2`
- Fuente inmutable: `SRC-NEXUSLUX-CONSTITUTION-V1-2`
- Regla canónica: `governance.constitution.nexuslux`
- Versión constitucional: `1.2`
- Estado: canon aprobado y vigente
- Responsable humano: Sebastián Portunato
- SHA-256 del ODT original: `adc2dd18e9a5cf2f3b9fd63dac32e6859d878185b29506b420c3fcdccd25936d`
- Tamaño del ODT original: `113825` bytes

## Preservación de la fuente

El conector de GitHub utilizado para esta operación no admite escribir directamente archivos binarios. Para no perder el original, `canon(4).odt` se conserva como un paquete Base64 íntegro dividido en fragmentos ordenados:

```text
sources/raw/SRC-NEXUSLUX-CONSTITUTION-V1-2/
├── manifest.yaml
└── parts/
    ├── canon(4).odt.b64.part-001
    ├── ...
    └── canon(4).odt.b64.part-019
```

La concatenación y decodificación de los 19 fragmentos reconstruye exactamente el ODT aportado. `config/verify-source.sh` verifica su tamaño y SHA-256.

## Trazabilidad

```text
fuente reconstruible
        ↓
registro SRC-NEXUSLUX-CONSTITUTION-V1-2
        ↓
decisión DEC-NEXUSLUX-CONSTITUTION-V1-2
        ↓
regla governance.constitution.nexuslux
        ↓
canon/snapshot.json
```

## Validación

```bash
sbe validate ./projects/nexuslux
bash ./projects/nexuslux/config/verify-source.sh
```
