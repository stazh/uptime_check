const axios = require('axios');
const fs = require('fs');
const path = require('path');

const URL_TO_CHECK = 'https://zentraleserien-hybridesuche.zh.ch';
const STATUS_FILE = path.join(__dirname, '..', 'status.json');
const HISTORY_FILE = path.join(__dirname, '..', 'history.json');

async function checkWebsite() {
    console.log(`Checking website: ${URL_TO_CHECK}`);
    
    const startTime = Date.now();
    let status = {
        url: URL_TO_CHECK,
        timestamp: new Date().toISOString(),
        status: 'unknown',
        responseTime: 0,
        statusCode: 0,
        error: null
    };

    try {
        const response = await axios.get(URL_TO_CHECK, {
            timeout: 30000, // 30 seconds timeout
            headers: {
                'User-Agent': 'Uptime-Monitor/1.0.0'
            }
        });
        
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        
        status = {
            ...status,
            status: response.status >= 200 && response.status < 300 ? 'online' : 'offline',
            responseTime: responseTime,
            statusCode: response.status
        };
        
        console.log(`✅ Website is online - Status: ${response.status} - Response time: ${responseTime}ms`);
        
    } catch (error) {
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        
        status = {
            ...status,
            status: 'offline',
            responseTime: responseTime,
            statusCode: error.response ? error.response.status : 0,
            error: error.message
        };
        
        console.log(`❌ Website is offline - Error: ${error.message}`);
    }

    return status;
}

function saveStatus(status) {
    try {
        fs.writeFileSync(STATUS_FILE, JSON.stringify(status, null, 2));
        console.log('Status saved to status.json');
    } catch (error) {
        console.error('Error saving status:', error);
    }
}

function saveToHistory(status) {
    try {
        let history = [];
        
        // Read existing history if file exists
        if (fs.existsSync(HISTORY_FILE)) {
            const historyData = fs.readFileSync(HISTORY_FILE, 'utf8');
            history = JSON.parse(historyData);
        }
        
        // Add new status to history
        history.push(status);
        
        // Keep only last 1000 entries to prevent file from growing too large
        if (history.length > 1000) {
            history = history.slice(-1000);
        }
        
        fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2));
        console.log('Status added to history.json');
        
    } catch (error) {
        console.error('Error saving to history:', error);
    }
}

function calculateUptime() {
    try {
        if (!fs.existsSync(HISTORY_FILE)) {
            return { uptime: 0, totalChecks: 0, onlineChecks: 0 };
        }
        
        const historyData = fs.readFileSync(HISTORY_FILE, 'utf8');
        const history = JSON.parse(historyData);
        
        const totalChecks = history.length;
        const onlineChecks = history.filter(check => check.status === 'online').length;
        const uptime = totalChecks > 0 ? (onlineChecks / totalChecks) * 100 : 0;
        
        return { uptime: uptime.toFixed(2), totalChecks, onlineChecks };
        
    } catch (error) {
        console.error('Error calculating uptime:', error);
        return { uptime: 0, totalChecks: 0, onlineChecks: 0 };
    }
}

async function main() {
    console.log('Starting uptime check...');
    
    const status = await checkWebsite();
    const uptimeStats = calculateUptime();
    
    // Add uptime statistics to status
    status.uptime = uptimeStats;
    
    saveStatus(status);
    saveToHistory(status);
    
    console.log(`Uptime: ${uptimeStats.uptime}% (${uptimeStats.onlineChecks}/${uptimeStats.totalChecks} checks)`);
    console.log('Uptime check completed!');
}

// Run the main function
main().catch(console.error);
