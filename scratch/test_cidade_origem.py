import unittest
import sys
import os

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.companies import get_company
from backend.app.companies.lactalis import (
    LactalisPernoiteCompany,
    LactalisDiariaGarantidaCompany,
    LactalisDiariaParadaCompany,
    LactalisSpecialBaseCompany,
)
from backend.app.companies.dpa import DPACompany
from backend.app.companies.latam import LatamCompany

class TestCidadeOrigem(unittest.TestCase):

    def test_lactalis_diaria_no_cliente(self):
        company = get_company("LACTALIS DIARIA NO CLIENTE")
        self.assertIsInstance(company, LactalisSpecialBaseCompany)
        self.assertEqual(company.get_cidade_origem("Salvador"), "Simões filho")

    def test_lactalis_pernoite(self):
        company = get_company("LACTALIS PERNOITE")
        self.assertIsInstance(company, LactalisSpecialBaseCompany)
        self.assertEqual(company.get_cidade_origem("Feira de Santana"), "Simões filho")

    def test_lactalis_diaria_em_rota(self):
        company = get_company("LACTALIS DIARIA EM ROTA")
        self.assertIsInstance(company, LactalisSpecialBaseCompany)
        self.assertEqual(company.get_cidade_origem("Vitória da Conquista"), "Simões filho")

    def test_lactalis_diaria_garantida(self):
        company = get_company("LACTALIS DIARIA GARANTIDA")
        self.assertIsInstance(company, LactalisSpecialBaseCompany)
        self.assertEqual(company.get_cidade_origem("Camaçari"), "Simões filho")

    def test_lactalis_diaria_parada(self):
        company = get_company("LACTALIS BA")
        self.assertIsInstance(company, LactalisDiariaParadaCompany)
        self.assertEqual(company.get_cidade_origem("Salvador"), "Salvador")

    def test_dpa(self):
        company = get_company("DPA NESTLE")
        self.assertIsInstance(company, DPACompany)
        self.assertEqual(company.get_cidade_origem("J. Pessoa"), "J. Pessoa")

    def test_latam(self):
        company = get_company("LATAM AIRLINES")
        self.assertIsInstance(company, LatamCompany)
        self.assertEqual(company.get_cidade_origem("São Paulo"), "São Paulo")

if __name__ == "__main__":
    unittest.main()
