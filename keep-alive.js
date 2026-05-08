const https = require('https');
const http = require('http');

// Configuration - Changez ces URLs
const URLS = [
  'https://umbrella-free-pdf.onrender.com',
  'https://umbrella-free-pdf.onrender.com/api/health',
  'https://umbrella-free-pdf.onrender.com/status'
];

// User-Agents aléatoires pour simuler différents navigateurs
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
  'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
  'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36'
];

function sendRequest(url, delay = 0) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const client = url.startsWith('https') ? https : http;
      const randomUA = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
      
      const options = {
        headers: {
          'User-Agent': randomUA,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
          'Cache-Control': 'no-cache'
        }
      };
      
      console.log(`🌐 [${new Date().toISOString()}] Pinging: ${url}`);
      
      const req = client.get(url, options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          console.log(`✅ Status: ${res.statusCode} | Size: ${data.length} bytes | UA: ${randomUA.substring(0, 30)}...`);
          resolve({ url, status: res.statusCode });
        });
      });
      
      req.on('error', (err) => {
        console.log(`❌ Error: ${err.message}`);
        resolve({ url, status: 'error', error: err.message });
      });
      
      req.end();
    }, delay);
  });
}

async function simulateTraffic() {
  console.log(`\n🚀 Starting keep-alive simulation at ${new Date().toISOString()}\n`);
  console.log(`📊 Will ping ${URLS.length} URLs with random delays\n`);
  
  const promises = URLS.map((url, index) => sendRequest(url, index * 2000));
  await Promise.all(promises);
  
  console.log(`\n✅ Session completed at ${new Date().toISOString()}\n`);
  console.log('─'.repeat(60));
}

// Exécuter immédiatement
simulateTraffic();

// Si exécuté en continu (optionnel, pour développement local)
if (process.env.CONTINUOUS_MODE === 'true') {
  setInterval(simulateTraffic, 10 * 60 * 1000); // Toutes les 10 minutes
}
