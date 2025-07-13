# scripts/gather_keys_oauth2.py 

import threading
import cherrypy
import webbrowser
import urllib.parse
import fitbit

class OAuth2Server:
    """Serveur minimal CherryPy pour récupérer le code OAuth Fitbit."""
    success_html = (
        "<html><body>"
        "<h1>✅ Autorisation réussie ! Vous pouvez retourner sur l'application.</h1>"
        "</body></html>"
    )

    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.redirect_uri  = redirect_uri
        self.authentication_code = None

    def browser_authorize(self):
        # 1) Démarrer CherryPy en parallèle
        threading.Thread(target=self._start_server, daemon=True).start()

        # 2) Ouvrir l’URL d’authentification
        auth_url = (
            "https://www.fitbit.com/oauth2/authorize"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            "&scope=activity%20heartrate%20sleep%20nutrition%20weight"
            "&expires_in=604800"
        )
        print("🌍 Ouverture de l'URL Fitbit dans le navigateur...")
        webbrowser.open_new(auth_url)

        # 3) Attendre que le code soit récupéré via /callback
        while self.authentication_code is None:
            pass

        # 4) Créer un client Fitbit avec le code obtenu
        fb = fitbit.Fitbit(
            self.client_id,
            self.client_secret,
            oauth2=True,
            redirect_uri=self.redirect_uri
        )
        fb.client.fetch_access_token(self.authentication_code)
        return fb

    def _start_server(self):
        cherrypy.config.update({
            'server.socket_host': '127.0.0.1',
            'server.socket_port': urllib.parse.urlparse(self.redirect_uri).port,
            'engine.autoreload.on': False,
        })
        cherrypy.quickstart(self)

    @cherrypy.expose
    def callback(self, code=None, **params):
        if code:
            self.authentication_code = code
            threading.Thread(target=cherrypy.engine.exit).start()
            return self.success_html
        return "❌ Erreur d'autorisation."

def get_fitbit_client(client_id, client_secret, redirect_uri='http://127.0.0.1:5000/callback'):
    """
    Authentifie l'utilisateur à chaque démarrage sans sauvegarde locale.
    """
    print("🔐 Authentification Fitbit en direct (aucune sauvegarde locale)...")
    server = OAuth2Server(client_id, client_secret, redirect_uri)
    fb = server.browser_authorize()
    print("✅ Fitbit connecté avec un token temporaire.")
    return fb
