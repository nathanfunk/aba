#!/usr/bin/env node
/**
 * Test script to verify tool calls display correctly in the web UI
 * Uses Playwright to automate browser interaction
 */

import { chromium } from 'playwright';

async function testToolCallDisplay() {
  console.log('🚀 Starting Playwright test...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the web UI
    console.log('📍 Navigating to http://localhost:8000');
    await page.goto('http://localhost:8000');
    await page.waitForTimeout(2000);

    // Wait for connection
    console.log('⏳ Waiting for WebSocket connection...');
    await page.waitForSelector('.connected', { timeout: 10000 });
    console.log('✅ Connected to server\n');

    // Find the input field and send a message that will trigger tool calls
    console.log('💬 Sending test message that triggers tool calls...');
    const input = await page.locator('textarea, input[type="text"]').first();
    await input.fill('Please read the README.md file and tell me what this project does');

    // Submit the message
    await page.keyboard.press('Enter');
    console.log('✅ Message sent\n');

    // Wait for tool calls to appear
    console.log('⏳ Waiting for tool calls to appear...');
    await page.waitForSelector('.tool-call', { timeout: 30000 });
    console.log('✅ Tool calls appeared!\n');

    // Wait for the full response to complete (input should be enabled again)
    console.log('⏳ Waiting for response to complete...');
    await page.waitForTimeout(8000); // Wait for streaming to finish
    console.log('✅ Response completed!\n');

    // Check the order of elements
    console.log('📊 Analyzing element order...\n');

    const messages = await page.locator('.message').all();
    console.log(`Found ${messages.length} messages\n`);

    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      const role = await msg.getAttribute('class');
      const content = await msg.locator('.message-content').textContent();
      const toolCalls = await msg.locator('.tool-call').all();

      console.log(`Message ${i + 1}:`);
      console.log(`  Role: ${role}`);
      console.log(`  Content: ${content.substring(0, 60)}${content.length > 60 ? '...' : ''}`);
      console.log(`  Tool calls: ${toolCalls.length}`);

      if (toolCalls.length > 0) {
        for (let j = 0; j < toolCalls.length; j++) {
          const toolName = await toolCalls[j].locator('.tool-name').textContent();
          const toolResult = await toolCalls[j].locator('.tool-result').textContent().catch(() => 'pending...');
          console.log(`    Tool ${j + 1}: ${toolName}`);
          console.log(`    Result: ${toolResult.substring(0, 50)}${toolResult.length > 50 ? '...' : ''}`);
        }
      }
      console.log('');
    }

    // Scroll to top to see everything
    console.log('📜 Scrolling to top...');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);

    // Take a screenshot
    console.log('📸 Taking screenshot...');
    await page.screenshot({ path: 'tool-display-test.png', fullPage: true });
    console.log('✅ Screenshot saved to tool-display-test.png\n');

    // Also check if tool calls are actually visible in the DOM
    const toolCallsVisible = await page.locator('.tool-call').count();
    console.log(`🔍 Tool calls visible in DOM: ${toolCallsVisible}\n`);

    // Check the exact position and styling of the tool call
    if (toolCallsVisible > 0) {
      const toolCall = page.locator('.tool-call').first();
      const boundingBox = await toolCall.boundingBox();
      console.log(`📐 Tool call position:`, boundingBox);

      const isVisible = await toolCall.isVisible();
      console.log(`👁️  Tool call isVisible(): ${isVisible}\n`);

      // Get the parent message HTML
      const messageHTML = await page.locator('.message.agent').innerHTML();
      console.log(`📝 Agent message HTML structure:\n${messageHTML.substring(0, 500)}...\n`);
    }

    // Verify chronological order
    console.log('✅ Test complete! Check the screenshot and console output above.\n');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'tool-display-error.png', fullPage: true });
    console.log('📸 Error screenshot saved to tool-display-error.png');
  } finally {
    await browser.close();
  }
}

testToolCallDisplay().catch(console.error);
