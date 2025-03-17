const QRCode = require('qrcode');
const { v4: uuidv4 } = require('uuid');

exports.handler = async function(event, context) {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    // Generate unique token
    const token = uuidv4();
    const expiry = new Date();
    expiry.setHours(expiry.getHours() + 24);

    // Generate QR code
    const qrUrl = `${process.env.URL}/mark-attendance?token=${token}`;
    const qrImage = await QRCode.toDataURL(qrUrl);

    return {
      statusCode: 200,
      body: JSON.stringify({
        qrCode: qrImage,
        token: token,
        expiry: expiry.toISOString()
      })
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Error generating QR code' })
    };
  }
}
