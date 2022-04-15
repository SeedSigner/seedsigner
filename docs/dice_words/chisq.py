from collections import defaultdict
from optparse import OptionParser
from scipy.stats import chi2, chisquare

def read_data_dice(filename: str, faces=None):
    uniques = defaultdict(int)
    with open(filename, 'r') as f:
        for line in f:
            for throw in line.split():
                uniques[int(throw)] += 1
    if faces is None:
        faces = max(uniques.keys())

    return [uniques[i + 1] for i in range(faces)]

def compute_chi2_stat(counts, expected):
    return 

def print_data(counts, expected):
    print("Face | Observed | Expected")
    for i in range(len(counts)):
        print("{:>4} | {:>8} | {:>8.5f}".format(i + 1, counts[i], expected))

parser = OptionParser(usage='Usage: %prog [options] filename')
parser.add_option("-t", "--target", dest="target", type="float", default=0.80, help="probability of passing a fair die, default: 0.80")
parser.add_option("-f", "--faces", dest="faces", type="int", help="number of faces, inferred from rolls if not specified")
(options, args) = parser.parse_args()
if len(args) != 1: parser.error('filename is required')

counts = read_data_dice(args[0], options.faces)
faces = len(counts)
total = sum(counts)
print('Faces: {}, Rolls: {}'.format(faces, total))

expected = total / faces
print_data(counts, expected)

(chi2_stat, pvalue) = chisquare(counts)
z = chi2.ppf(options.target, df=faces - 1)
print('Result: {}, Target: {}, Stat: {}, PValue: {}'.format('PASS' if chi2_stat < z else 'FAIL', z, chi2_stat, pvalue))

