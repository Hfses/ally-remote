// Service worker mínimo: só existe para permitir "Adicionar à tela inicial"
// como app. Sem cache offline de propósito — o app não funciona sem o servidor.
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', () => {});
