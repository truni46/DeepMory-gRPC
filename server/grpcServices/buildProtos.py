"""
Compile .proto files into Python gRPC stubs.
Run from server/ directory:  python -m grpcServices.buildProtos
"""
import subprocess
import os
import sys

PROTO_DIR = os.path.join(os.path.dirname(__file__), "protos")
OUT_DIR = os.path.join(os.path.dirname(__file__), "generated")


def buildProtos():
    os.makedirs(OUT_DIR, exist_ok=True)

    protoFiles = [f for f in os.listdir(PROTO_DIR) if f.endswith(".proto")]
    if not protoFiles:
        print("No .proto files found")
        return

    for proto in protoFiles:
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={PROTO_DIR}",
            f"--python_out={OUT_DIR}",
            f"--grpc_python_out={OUT_DIR}",
            f"--pyi_out={OUT_DIR}",
            os.path.join(PROTO_DIR, proto),
        ]
        print(f"Compiling {proto}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
            sys.exit(1)
        print(f"  OK")

    initPath = os.path.join(OUT_DIR, "__init__.py")
    if not os.path.exists(initPath):
        open(initPath, "w").close()

    fixImports(OUT_DIR)
    print(f"\nDone. Generated files in {OUT_DIR}")


def fixImports(outDir):
    """Fix relative imports in generated *_grpc.py files."""
    for filename in os.listdir(outDir):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(outDir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        newContent = content
        newContent = newContent.replace(
            "import common_pb2", "from grpcServices.generated import common_pb2"
        )
        newContent = newContent.replace(
            "import rag_pb2", "from grpcServices.generated import rag_pb2"
        )
        newContent = newContent.replace(
            "import memory_pb2", "from grpcServices.generated import memory_pb2"
        )
        newContent = newContent.replace(
            "import agents_pb2", "from grpcServices.generated import agents_pb2"
        )

        if newContent != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(newContent)
            print(f"  Fixed imports in {filename}")


if __name__ == "__main__":
    buildProtos()
