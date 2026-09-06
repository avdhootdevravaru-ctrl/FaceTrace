// Hardhat deployment script for VerificationRegistry
// Uses ethers directly to connect to the local Hardhat node

const { ethers } = require("ethers");
const fs = require("fs");

async function main() {
  console.log("=".repeat(50));
  console.log("  FaceTrace - VerificationRegistry Deployment");
  console.log("=".repeat(50));
  console.log();

  // Connect to local Hardhat node
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

  // Get the first account (prefunded by Hardhat)
  const wallet = new ethers.Wallet(
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    provider
  );

  console.log("Deployer account:", wallet.address);
  console.log("Account balance:", (await provider.getBalance(wallet.address)).toString());
  console.log();

  console.log("Deploying VerificationRegistry...");

  // Read contract artifact
  const artifact = JSON.parse(fs.readFileSync("./artifacts/contracts/VerificationRegistry.sol/VerificationRegistry.json", "utf8"));

  // Create contract instance
  const factory = new ethers.ContractFactory(
    artifact.abi,
    artifact.bytecode,
    wallet
  );

  // Deploy
  const registry = await factory.deploy();
  await registry.waitForDeployment();
  const address = await registry.getAddress();

  console.log();
  console.log("=".repeat(50));
  console.log("  DEPLOYMENT SUCCESSFUL");
  console.log("=".repeat(50));
  console.log();
  console.log("Contract address:", address);
  console.log("Network:         Hardhat Local (chain ID 31337)");
  console.log();
  console.log("Next steps:");
  console.log("1. Copy the contract address above");
  console.log("2. Add to your project's .env file:");
  console.log("   BLOCKCHAIN_MODE=hardhat");
  console.log("   RPC_URL=http://127.0.0.1:8545");
  console.log("   CONTRACT_ADDRESS=" + address);
  console.log();

  // Write deployment info
  const deploymentInfo = {
    network: "hardhat-local",
    chainId: 31337,
    contractAddress: address,
    deployer: wallet.address,
    timestamp: new Date().toISOString(),
    rpcUrl: "http://127.0.0.1:8545"
  };
  fs.writeFileSync(
    "deployment-info.json",
    JSON.stringify(deploymentInfo, null, 2)
  );
  console.log("Deployment info saved to: deployment-info.json");

  // Test the contract
  console.log();
  console.log("Testing contract...");
  const totalRecords = await registry.totalRecords();
  console.log("Total records:", totalRecords.toString());
  console.log("Contract deployed and working!");
}

main()
  .then(() => {
    console.log();
    process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
