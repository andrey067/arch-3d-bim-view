# Testando Realidade Aumentada (AR)

Este documento explica como testar a funcionalidade de AR em dispositivos reais.

## Pre-requisitos

- Modelo 3D convertido (GLB) e pronto para visualizacao
- Backend rodando localmente
- Dispositivo Android (Chrome) ou iOS (Safari)

## Configuracao do Ambiente HTTPS

AR requer HTTPS para funcionar. Para testar localmente, voce precisa expor seu backend via HTTPS.

### Opcao 1: ngrok (Recomendado)

1. Instale o ngrok:
   ```bash
   # macOS
   brew install ngrok

   # Ou baixe de https://ngrok.com/download
   ```

2. Configure seu token (obtenha em https://dashboard.ngrok.com/get-started/your-authtoken):
   ```bash
   ngrok config add-authtoken SEU_TOKEN
   ```

3. Inicie o tunnel para o backend:
   ```bash
   ngrok http 8000
   ```

4. Copie a URL HTTPS fornecida (ex: `https://abc123.ngrok.io`)

5. Configure no `.env` do backend:
   ```bash
   PUBLIC_BASE_URL=https://abc123.ngrok.io
   CORS_ORIGINS=["https://abc123.ngrok.io"]
   ```

### Opcao 2: Cloudflare Tunnel

1. Instale cloudflared:
   ```bash
   # macOS
   brew install cloudflare/cloudflare/cloudflared
   ```

2. Inicie o tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. Use a URL HTTPS fornecida

### Opcao 3: mkcert (Certificado Local)

1. Instale mkcert:
   ```bash
   brew install mkcert
   mkcert -install
   ```

2. Gere certificados:
   ```bash
   mkcert localhost 127.0.0.1 ::1
   ```

3. Configure o backend para usar HTTPS com os certificados gerados

## Testando em Android

1. Acesse a URL HTTPS do modelo no Chrome do dispositivo
2. Faca login e navegue ate um modelo com conversao concluida
3. Clique em "Visualizar em AR"
4. O Scene Viewer deve abrir automaticamente
5. Aponte a camera para uma superficie plana
6. Toque para posicionar o modelo
7. Use gestos para rotacionar e escalar

### Troubleshooting Android

| Problema | Solucao |
|----------|---------|
| Botao AR nao aparece | Verifique se esta em HTTPS e se o dispositivo suporta WebXR |
| Scene Viewer nao abre | Atualize o Google Play Services |
| Modelo nao aparece na AR | Verifique se o GLB esta valido |
| "AR nao suportado" | Use Chrome 79+ ou Samsung Internet |

## Testando em iOS

1. Acesse a URL HTTPS do modelo no Safari do dispositivo
2. Faca login e navegue ate um modelo com conversao concluida
3. Toque no icone AR (cubo 3D) que aparece sobre o modelo
4. O Quick Look deve abrir
5. Aponte a camera para uma superficie plana
6. Toque para posicionar o modelo

### Troubleshooting iOS

| Problema | Solucao |
|----------|---------|
| Botao AR nao aparece | Verifique se esta usando Safari (Chrome nao suporta Quick Look) |
| Quick Look nao abre | iOS 12+ necessario |
| Modelo nao renderiza | Verifique se o GLB esta acessivel via HTTPS |
| "Formato nao suportado" | Alguns modelos complexos podem nao funcionar |

## Testando em Desktop

1. Acesse a URL do modelo em qualquer navegador desktop
2. O botao AR **nao deve aparecer**
3. Deve exibir a mensagem: "AR indisponivel neste dispositivo"
4. A visualizacao 3D normal deve funcionar com controles de orbita

## Validacao da Funcionalidade

### Checklist

- [ ] Android: Botao "Visualizar em AR" aparece em HTTPS
- [ ] Android: Scene Viewer abre ao clicar no botao
- [ ] Android: Modelo pode ser posicionado no ambiente
- [ ] iOS: Botao AR aparece no Safari em HTTPS
- [ ] iOS: Quick Look abre ao clicar no botao
- [ ] iOS: Modelo pode ser posicionado no ambiente
- [ ] Desktop: Botao AR nao aparece
- [ ] Desktop: Mensagem informativa e exibida
- [ ] HTTP: Banner "AR requer HTTPS" aparece em desenvolvimento
- [ ] Viewers: AR funciona no viewer privado (`/viewer/:fileId`)
- [ ] Viewers: AR funciona no viewer publico (`/s/:token`)

## Cenarios de Teste

### 1. Dispositivo compativel + HTTPS
**Resultado esperado**: Botao AR visivel, abre Scene Viewer/Quick Look

### 2. Dispositivo compativel + HTTP
**Resultado esperado**: Banner de aviso, botao AR oculto

### 3. Desktop (qualquer protocolo)
**Resultado esperado**: Mensagem "AR indisponivel neste dispositivo"

### 4. Dispositivo incompativel + HTTPS
**Resultado esperado**: Botao AR oculto, mensagem informativa

### 5. Erro ao abrir AR
**Resultado esperado**: Mensagem de erro amigavel, viewer 3D continua funcionando

## Limitacoes Conhecidas

1. **USDZ nao implementado**: Quick Look no iOS pode ter limitacoes com GLB em alguns cenarios. Registrado como melhoria futura.

2. **Modelos complexos**: Modelos muito grandes (>50MB) podem ter performance inferior em AR.

3. **Superficies**: A deteccao de superficie depende do hardware do dispositivo e iluminacao.

4. **Navegadores**: Apenas Chrome (Android) e Safari (iOS) suportam AR nativo.

## Links Uteis

- [model-viewer AR Documentation](https://modelviewer.dev/docs/index.html#augmentedReality)
- [WebXR Device API](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API)
- [Apple Quick Look](https://developer.apple.com/augmented-reality/quick-look/)
- [Google Scene Viewer](https://developers.google.com/ar/develop/scene-viewer)
