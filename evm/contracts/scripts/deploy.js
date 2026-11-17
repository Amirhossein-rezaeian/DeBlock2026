const hre = require("hardhat");

async function main() {
  const factory = await hre.ethers.getContractFactory("UrbanTwinRegistry");
  const registry = await factory.deploy();

  await registry.waitForDeployment();

  console.log("UrbanTwinRegistry:", await registry.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
