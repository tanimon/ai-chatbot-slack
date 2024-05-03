import * as apprunner from "@aws-cdk/aws-apprunner-alpha";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export class MainStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new apprunner.Service(this, "Service", {
      source: apprunner.Source.fromAsset({
        imageConfiguration: { port: 8000 },
        asset: new cdk.aws_ecr_assets.DockerImageAsset(this, "ImageAsset", {
          directory: "../server",
        }),
      }),
      autoDeploymentsEnabled: true,
    });
  }
}
