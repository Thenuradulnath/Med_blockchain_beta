const MedicalVault = artifacts.require("MedicalVault");

module.exports = function (deployer) {
  deployer.deploy(MedicalVault);
};
