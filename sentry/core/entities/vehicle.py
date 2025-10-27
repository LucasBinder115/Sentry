from typing import Optional


class Vehicle:
    """
    Entidade que representa um Veículo no sistema.

    Atributos:
        id (int | None): Identificador único do veículo.
        plate (str): Placa do veículo (sempre em maiúsculas).
        model (str): Modelo do veículo.
        color (str | None): Cor do veículo (opcional).
        carrier_cnpj (str | None): CNPJ da transportadora associada (opcional).
    """

    def __init__(
        self,
        plate: str,
        model: str,
        color: Optional[str] = None,
        carrier_cnpj: Optional[str] = None,
        id: Optional[int] = None,
    ):
        if not plate or not plate.strip():
            raise ValueError("A placa do veículo é obrigatória.")
        if not model or not model.strip():
            raise ValueError("O modelo do veículo é obrigatório.")

        self.id = id
        self.plate = plate.strip().upper()
        self.model = model.strip()
        self.color = color.strip() if color else None
        self.carrier_cnpj = carrier_cnpj.strip() if carrier_cnpj else None

    def __repr__(self) -> str:
        return f"<Vehicle plate='{self.plate}' model='{self.model}'>"

    def to_dict(self) -> dict:
        """
        Converte o objeto para um dicionário, útil para serialização (ex: JSON).
        """
        return {
            "id": self.id,
            "plate": self.plate,
            "model": self.model,
            "color": self.color,
            "carrier_cnpj": self.carrier_cnpj,
        }