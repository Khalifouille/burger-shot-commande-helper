from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    # Vérifier si la requête correspond à celle que vous souhaitez réitérer
    if "bank__GetAllPlayerAccount" in flow.request.pretty_url:
        print("Requête interceptée :", flow.request.pretty_url)
        
        # Afficher les en-têtes et le corps de la requête
        print("En-têtes :", flow.request.headers)
        print("Corps :", flow.request.text)

        # Réitérer la requête
        import requests
        response = requests.post(
            flow.request.pretty_url,
            headers=dict(flow.request.headers),
            data=flow.request.text
        )
        
        # Afficher la réponse
        print("Réponse :", response.status_code, response.text)