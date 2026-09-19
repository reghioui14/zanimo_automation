const fs = require('fs');
const path = require('path');

const authPath = '/app/.wwebjs_auth';
const lockFiles = ['SingletonLock', 'SingletonCookie', 'SingletonSocket'];

function removeLocks(dir) {
    if (!fs.existsSync(dir)) return;
    lockFiles.forEach(file => {
        const lockPath = path.join(dir, file);
        try {
            fs.lstatSync(lockPath);
            fs.unlinkSync(lockPath);
            console.log(`Removed stale lock: ${lockPath}`);
        } catch (e) {}
    });
    try {
        fs.readdirSync(dir).forEach(sub => {
            const subPath = path.join(dir, sub);
            if (fs.statSync(subPath).isDirectory()) {
                removeLocks(subPath);
            }
        });
    } catch(e) {}
}

removeLocks(authPath);

const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const app = express();
app.use(express.json({limit:'20mb'}));
let ready = false;
let lastQR = '';

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: '/app/.wwebjs_auth' }),
  puppeteer: { 
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium', 
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
      '--disable-dev-shm-usage'
    ] 
  }
});
client.on('qr', qr => { lastQR = qr; console.log('SCAN THIS QR WITH WHATSAPP:'); qrcode.generate(qr, {small: true}); });
client.on('ready', () => { ready = true; console.log('WhatsApp ready'); });
client.on('disconnected', reason => { ready = false; console.log('WhatsApp disconnected', reason); });
client.initialize();

function chatId(to){
  let n = String(to).replace(/[^0-9]/g,'');
  if(!n) throw new Error('Missing phone number');
  return n + '@c.us';
}

app.get('/status', (req,res)=>res.json({ready, hasQR: !!lastQR}));

app.post('/send-media', async (req,res)=>{
  try{
    if(!ready) return res.status(503).json({ok:false, error:'WhatsApp not ready. Scan QR: docker logs whatsapp'});
    const {to, paths, caption} = req.body;
    if(!Array.isArray(paths) || !paths.length) return res.status(400).json({ok:false,error:'paths[] required'});
    const id = chatId(to);
    let sent=[];
    for(const p of paths){
      if(!fs.existsSync(p)) throw new Error('File not found: '+p);
      const media = MessageMedia.fromFilePath(p);
      const msg = await client.sendMessage(id, media, {caption: caption || ''});
      sent.push(msg && msg.id ? msg.id._serialized : null);
    }
    res.json({ok:true, sent});
  }catch(e){ res.status(500).json({ok:false, error:e.message}); }
});

app.post('/send-text', async (req,res)=>{
  try{
    if(!ready) return res.status(503).json({ok:false, error:'WhatsApp not ready'});
    const msg = await client.sendMessage(chatId(req.body.to), req.body.text || '');
    res.json({ok:true, id: msg && msg.id ? msg.id._serialized : null});
  }catch(e){ res.status(500).json({ok:false, error:e.message}); }
});

app.listen(3000, ()=>console.log('WhatsApp gateway on :3000'));