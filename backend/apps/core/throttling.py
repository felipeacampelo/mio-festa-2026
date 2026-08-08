from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    # ScopedRateThrottle le o "scope" do atributo throttle_scope da view, mas
    # os decorators de function-based view (@api_view) nao propagam esse
    # atributo pra classe interna que ele gera - o scope sempre virava None
    # e a checagem de limite nunca era ativada. Aqui o scope e fixo na
    # propria classe, sem depender da view, exatamente como o AnonRateThrottle
    # nativo do DRF faz para o escopo "anon".
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
