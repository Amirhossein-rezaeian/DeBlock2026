const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("UrbanTwinRegistry", function () {
  async function deployRegistry() {
    const [owner, other] = await ethers.getSigners();
    const factory = await ethers.getContractFactory("UrbanTwinRegistry");
    const registry = await factory.deploy();

    await registry.waitForDeployment();

    return { registry, owner, other };
  }

  it("stores and verifies a record hash", async function () {
    const { registry } = await deployRegistry();
    const digest = ethers.keccak256(ethers.toUtf8Bytes("sensor-record-1"));

    await registry.anchorRecord("URBAN-001", 1, digest, 1);

    expect(
      await registry.verifyRecord("URBAN-001", 1, digest)
    ).to.equal(true);

    expect(
      await registry.verifyRecord("URBAN-001", 1, ethers.ZeroHash)
    ).to.equal(false);
  });

  it("rejects duplicate record anchors", async function () {
    const { registry } = await deployRegistry();
    const digest = ethers.keccak256(ethers.toUtf8Bytes("sensor-record-1"));

    await registry.anchorRecord("URBAN-001", 1, digest, 1);

    await expect(
      registry.anchorRecord("URBAN-001", 1, digest, 1)
    ).to.be.revertedWith("record already anchored");
  });

  it("restricts write access to the contract owner", async function () {
    const { registry, other } = await deployRegistry();
    const digest = ethers.keccak256(ethers.toUtf8Bytes("sensor-record-1"));

    await expect(
      registry.connect(other).anchorRecord("URBAN-001", 1, digest, 1)
    ).to.be.revertedWith("not authorized");
  });
});
