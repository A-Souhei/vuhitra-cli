import argparse
from src.agent import generate

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-m', '--model', default='llama3')
    p.add_argument('-p', '--prompt', required=True)
    a = p.parse_args()
    response = generate(a.model, a.prompt)
    print(response)

if __name__ == '__main__':
    main()
