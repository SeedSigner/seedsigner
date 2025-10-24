import pytest

TEST_PASSPHRASES = ["muhpassphrase", "áéíóúàèìòùâêîôûãõëïüÿăąæøåðçñşțćłšžčřňťđĺŕľĵĝħÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕËÏÜŸĂĄÆØÅÐÇÑŞȚĆŁŠŽČŘŇŤĐĹŔĽĴĜĦ"]
@pytest.fixture(scope="session", params=TEST_PASSPHRASES)
def passphrase(request):
    return request.param