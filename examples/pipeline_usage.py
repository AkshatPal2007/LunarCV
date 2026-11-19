"""Register real file paths. Outputs are diagnostics until independently checked."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from lunarcv.engine import RegistrationConfig, RegistrationEngine


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("reference",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    result=RegistrationEngine(RegistrationConfig()).run(args.source,args.reference,args.output)
    print(result.metrics["quality_decision"])
