"""Entrenamiento y preparación de modelos para ZENIT:
1) TFT (Temporal Fusion Transformer): modelo de series temporales para predicción de desabasto.
2) LLM (Ollama): configuración y preparación de modelos locales con el prompt de identidad oficial de Zenit.

Carga el prompt de identidad desde `OpenJarvis/prompts/zenit_system_prompt.md`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

# Asegurar que el directorio raíz de OpenJarvis esté en sys.path
_OPENJARVIS_DIR = Path(__file__).resolve().parent.parent
if str(_OPENJARVIS_DIR) not in sys.path:
    sys.path.insert(0, str(_OPENJARVIS_DIR))

try:
    from modelo.datos import (
        CKPT_PATH,
        CSV_PATH,
        CrossEntropyPonderada,
        calcular_peso_positivo,
        crear_dataset_entrenamiento,
        preparar_datos,
    )
    from modelo.predecir import limitar_hilos_cpu
except ImportError:
    from datos import (  # type: ignore
        CKPT_PATH,
        CSV_PATH,
        CrossEntropyPonderada,
        calcular_peso_positivo,
        crear_dataset_entrenamiento,
        preparar_datos,
    )
    from predecir import limitar_hilos_cpu  # type: ignore

# Constantes por defecto para TFT
SEMILLA_DEFAULT = 42
HIDDEN_SIZE_DEFAULT = 16
ATTENTION_HEAD_SIZE_DEFAULT = 2
DROPOUT_DEFAULT = 0.1
LEARNING_RATE_DEFAULT = 0.005
BATCH_SIZE_DEFAULT = 128
MAX_EPOCHS_DEFAULT = 45

# Ruta del prompt de identidad externo
PROMPT_PATH_DEFAULT = _OPENJARVIS_DIR / "prompts" / "zenit_system_prompt.md"


def cargar_prompt_sistema(prompt_path: Optional[Path] = None) -> str:
    """Carga el prompt de sistema desde el archivo externo markdown."""
    ruta = prompt_path or PROMPT_PATH_DEFAULT
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo de prompt en: {ruta}")
    return ruta.read_text(encoding="utf-8").strip()


def entrenar_tft(
    csv_path: Path = CSV_PATH,
    ckpt_path: Path = CKPT_PATH,
    hidden_size: int = HIDDEN_SIZE_DEFAULT,
    attention_head_size: int = ATTENTION_HEAD_SIZE_DEFAULT,
    dropout: float = DROPOUT_DEFAULT,
    learning_rate: float = LEARNING_RATE_DEFAULT,
    batch_size: int = BATCH_SIZE_DEFAULT,
    max_epochs: int = MAX_EPOCHS_DEFAULT,
    accelerator: str = "cpu",
    seed: int = SEMILLA_DEFAULT,
) -> Dict[str, object]:
    from modelo.entrenamiento import entrenar_validado
    return entrenar_validado(csv_path, ckpt_path, hidden_size, attention_head_size,
                            dropout, learning_rate, batch_size, max_epochs, accelerator, seed)


def preparar_modelo_ollama(
    modelo_base: str = "qwen2.5:3b",
    nombre_destino: str = "zenit",
    prompt_path: Optional[Path] = None,
    temperatura: float = 0.2,
) -> Dict[str, Any]:
    """Crea o acondiciona un modelo en Ollama inyectando el Modelfile con el prompt de Zenit."""
    system_prompt = cargar_prompt_sistema(prompt_path)

    modelfile_content = f"""FROM {modelo_base}
PARAMETER temperature {temperatura}
SYSTEM \"\"\"{system_prompt}\"\"\"
"""

    modelfile_path = _OPENJARVIS_DIR / "Modelfile.zenit"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"Modelfile generado en: {modelfile_path} para modelo '{nombre_destino}' basado en '{modelo_base}'")

    # Intentar ejecutar `ollama create`
    comando = ["ollama", "create", nombre_destino, "-f", str(modelfile_path)]
    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=True,
        )
        salida = resultado.stdout.strip()
        print(f"Modelo {nombre_destino} creado exitosamente en Ollama:\n{salida}")
        return {
            "tipo_modelo": "OLLAMA",
            "modelo_base": modelo_base,
            "nombre_destino": nombre_destino,
            "modelfile": str(modelfile_path),
            "estado": "creado",
            "salida": salida,
        }
    except FileNotFoundError:
        print("Aviso: El comando 'ollama' no se encuentra en el PATH. El Modelfile quedó listo.")
        return {
            "tipo_modelo": "OLLAMA",
            "modelo_base": modelo_base,
            "nombre_destino": nombre_destino,
            "modelfile": str(modelfile_path),
            "estado": "modelfile_preparado",
            "detalle": "Ollama CLI no disponible en PATH para ejecutar 'ollama create'.",
        }
    except subprocess.CalledProcessError as exc:
        print(f"Error al ejecutar 'ollama create': {exc.stderr}")
        return {
            "tipo_modelo": "OLLAMA",
            "modelo_base": modelo_base,
            "nombre_destino": nombre_destino,
            "modelfile": str(modelfile_path),
            "estado": "error",
            "detalle": exc.stderr,
        }


# Alias para compatibilidad hacia atrás
def entrenar(
    csv_path: Path = CSV_PATH,
    ckpt_path: Path = CKPT_PATH,
    max_epochs: int = MAX_EPOCHS_DEFAULT,
) -> Dict[str, object]:
    """Función de conveniencia para mantener compatibilidad con versiones previas."""
    return entrenar_tft(csv_path=csv_path, ckpt_path=ckpt_path, max_epochs=max_epochs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrenamiento y configuración de modelos para ZENIT (TFT y LLM Ollama)."
    )
    subparsers = parser.add_subparsers(dest="comando", help="Comando a ejecutar")

    # Subcomando TFT
    parser_tft = subparsers.add_parser("tft", help="Entrenar modelo Temporal Fusion Transformer")
    parser_tft.add_argument("--csv", type=Path, default=CSV_PATH, help="Ruta al CSV de ventas")
    parser_tft.add_argument("--ckpt", type=Path, default=CKPT_PATH, help="Ruta de salida del checkpoint")
    parser_tft.add_argument("--hidden-size", type=int, default=HIDDEN_SIZE_DEFAULT, help="Tamaño de capa oculta")
    parser_tft.add_argument("--heads", type=int, default=ATTENTION_HEAD_SIZE_DEFAULT, help="Cabezas de atención")
    parser_tft.add_argument("--dropout", type=float, default=DROPOUT_DEFAULT, help="Tasa de dropout")
    parser_tft.add_argument("--lr", type=float, default=LEARNING_RATE_DEFAULT, help="Learning rate")
    parser_tft.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT, help="Tamaño de batch")
    parser_tft.add_argument("--epochs", type=int, default=MAX_EPOCHS_DEFAULT, help="Número de épocas")
    parser_tft.add_argument("--accelerator", type=str, default="cpu", choices=["cpu", "gpu"], help="Dispositivo")
    parser_tft.add_argument("--activar", action="store_true", help="Activar candidata validada conservando respaldo")
    parser_tft.add_argument("--evaluar", action="store_true", help="Evaluar métricas tras entrenar")

    # Subcomando OLLAMA
    parser_ollama = subparsers.add_parser("ollama", help="Configurar modelo local Ollama con el prompt de Zenit")
    parser_ollama.add_argument("--base", type=str, default="qwen2.5:3b", help="Modelo base en Ollama")
    parser_ollama.add_argument("--nombre", type=str, default="zenit", help="Nombre del modelo final a registrar")
    parser_ollama.add_argument("--prompt", type=Path, default=PROMPT_PATH_DEFAULT, help="Ruta del archivo de prompt")
    parser_ollama.add_argument("--temp", type=float, default=0.2, help="Temperatura de generación")

    # Parámetros retrocompatibles en raíz si no se usa subcomando
    parser.add_argument("--epochs", type=int, default=None, help="Épocas para entrenamiento TFT por defecto")
    parser.add_argument("--evaluar", action="store_true", help="Evaluar métricas TFT tras entrenar")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.comando == "ollama":
        resumen = preparar_modelo_ollama(
            modelo_base=args.base,
            nombre_destino=args.nombre,
            prompt_path=args.prompt,
            temperatura=args.temp,
        )
        print("\nResultado configuración Ollama:")
        print(json.dumps(resumen, indent=2, ensure_ascii=False))

    elif args.comando == "tft":
        resumen = entrenar_tft(
            csv_path=args.csv,
            ckpt_path=args.ckpt,
            hidden_size=args.hidden_size,
            attention_head_size=args.heads,
            dropout=args.dropout,
            learning_rate=args.lr,
            batch_size=args.batch_size,
            max_epochs=args.epochs,
            accelerator=args.accelerator,
        )
        print("\nEntrenamiento TFT completado:")
        for clave, valor in resumen.items():
            if not isinstance(valor, (dict, list)):
                print(f"  {clave}: {valor}")

        if args.evaluar:
            try:
                from modelo.predecir import evaluar_ultimos_27_dias
                reporte = evaluar_ultimos_27_dias(csv_path=args.csv, ckpt_path=Path(resumen["ckpt_path"]))
                print("\nEvaluación en los últimos 27 días:")
                for clave, valor in reporte.items():
                    if not isinstance(valor, (dict, list)):
                        print(f"  {clave}: {valor}")
            except Exception as exc:
                raise RuntimeError("Fallo la evaluacion") from exc

        if args.activar:
            from modelo.entrenamiento import activar_modelo
            activar_modelo(Path(resumen["ckpt_path"]), args.ckpt)

    else:
        # Modo por defecto (compatible con ejecución directa previa)
        epocas = args.epochs if args.epochs is not None else MAX_EPOCHS_DEFAULT
        resumen = entrenar(max_epochs=epocas)
        print("\nEntrenamiento TFT completado:")
        for clave, valor in resumen.items():
            if not isinstance(valor, (dict, list)):
                print(f"  {clave}: {valor}")

        if args.evaluar:
            try:
                from modelo.predecir import evaluar_ultimos_27_dias
                reporte = evaluar_ultimos_27_dias(csv_path=Path(resumen["csv_path"]), ckpt_path=Path(resumen["ckpt_path"]))
                print("\nEvaluación en los últimos 27 días:")
                for clave, valor in reporte.items():
                    if not isinstance(valor, (dict, list)):
                        print(f"  {clave}: {valor}")
            except Exception as exc:
                raise RuntimeError("Fallo la evaluacion") from exc


if __name__ == "__main__":
    main()
