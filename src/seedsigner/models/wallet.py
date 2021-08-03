class Wallet:

    QRLOW = 0
    QRMEDIUM = 1
    QRHIGH = 2

    def __init__(self, current_network, qr_density, policy) -> None:
        self.current_network = current_network

        if policy == "PKWSH" and self.current_network == "main":
            self.hardened_derivation = "m/48h/0h/0h/2h"
        elif policy == "PKWSH" and self.current_network == "test":
            self.hardened_derivation = "m/48h/1h/0h/2h"
        elif policy == "PKWPKH" and self.current_network == "main":
            self.hardened_derivation = "m/84h/0h/0h"
        elif policy == "PKWPKH" and self.current_network == "test":
            self.hardened_derivation = "m/84h/1h/0h"
        else:
            raise Exception("Unsupported Derivation Path or Policy")

        self.qrsize = 80 # Default
        self.set_qr_density(qr_density)
        self.cur_qr_density = qr_density
        self.cur_policy = policy

    def set_qr_density(self, density):
        self.cur_qr_density = density
        if density == Wallet.QRLOW:
            self.qrsize = 60
        elif density == Wallet.QRMEDIUM:
            self.qrsize = 80
        elif density == Wallet.QRHIGH:
            self.qrsize = 100

    def get_qr_density(self):
        return self.cur_qr_density

    def get_qr_density_name(self) -> str :
        if self.cur_qr_density == Wallet.QRLOW:
            return "Low"
        elif self.cur_qr_density == Wallet.QRMEDIUM:
            return "Medium"
        elif self.cur_qr_density == Wallet.QRHIGH:
            return "High"
        else:
            return "Unknown"

    def get_wallet_policy_name(self) -> str :
        if self.cur_policy == "PKWSH":
            return "Multi Sig"
        elif self.cur_policy == "PKWPKH":
            return "Single Sig"
        else:
            return self.cur_policy

    def get_wallet_policy(self) -> str:
        return self.cur_policy

    ###
    ### Network Related Methods
    ###

    def get_network(self) -> str:
        return self.current_network

    def get_hardened_derivation(self) -> str:
        return self.hardened_derivation

    def set_network(self, network) -> bool:
        return False