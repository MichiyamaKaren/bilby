import unittest
import os
import shutil
from context import tupak
import logging
import glob
import subprocess
from past.builtins import execfile


class Test(unittest.TestCase):
    outdir = 'outdir'
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.abspath(os.path.join(dir_path, os.path.pardir))

    @classmethod
    def setUpClass(self):
        if os.path.isdir(self.outdir):
            try:
                shutil.rmtree(self.outdir)
            except OSError:
                logging.warning(
                    "{} not removed prior to tests".format(self.outdir))

    @classmethod
    def tearDownClass(self):
        if os.path.isdir(self.outdir):
            try:
                shutil.rmtree(self.outdir)
            except OSError:
                logging.warning(
                    "{} not removed prior to tests".format(self.outdir))

    def test_examples(self):
        """ Loop over all examples to check they run """
        examples = glob.glob("examples/*/*.py")
        examples = ['examples/injection_examples/how_to_specify_the_prior.py',
                    'examples/injection_examples/change_sampled_parameters.py',
                    'examples/injection_examples/marginalized_likelihood.py',
                    'examples/injection_examples/create_your_own_source_model.py',
                    'examples/injection_examples/create_your_own_time_domain_source_model.py',
                    'examples/other_examples/alternative_likelihoods.py',
                    'examples/open_data_examples/GW150914.py',
                    'examples/open_data_examples/GW150914_minimal.py',
                    ]
        for filename in examples:
            print("Testing {}".format(filename))
            out = subprocess.check_output(["python", filename, "--test"])
            print(out)


if __name__ == '__main__':
    unittest.main()


