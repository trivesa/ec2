// Importing required modules
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios'); // Assuming axios is used for API requests

// Initialize express app
const app = express();
app.use(bodyParser.json()); // Parse JSON requests

// Route to generate the product listing
app.post('/generate-listing', async (req, res) => {
  const prompt = req.body.prompt;

  try {
    // Assuming you use OpenAI or another API for product listing generation
    const completion = await axios.post('https://api.openai.com/v1/completions', {
      prompt: prompt,
      max_tokens: 200,
    }, {
      headers: {
        'Authorization':' sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zg',
        'Content-Type': 'application/json'
      }
    });

    const generatedListing = completion.data.choices[0].text;
    res.json({ listing: generatedListing });

  } catch (error) {
    console.error('Error generating listing:', error);  // Log the full error object

    // Log additional error details if available
    if (error.response) {
      console.error('Error response status:', error.response.status);  // Log status code
      console.error('Error response data:', error.response.data);      // Log response data
    }

    res.status(500).json({ error: 'An error occurred while generating the listing.' });
  }
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
