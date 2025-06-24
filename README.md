LIVE: https://thesis-g13y.onrender.com/


# Deployment Documentation using SageMaker

https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#bring-your-own-model

## Sample JSON for this endpoint

```json
{
    "image_url": "https://rpi-upload-bucket.s3.ap-southeast-1.amazonaws.com/Dataset/samples/stage_1/image_20250622_175142.jpg",
    "sample_id": "111"
}
```

# TODO

1. Create a new function that detects microplastics using the trained model (.pth) [this already exists] given an s3 image url and its sample id (The url and sampleID can be taken from DynamoDB). This returns an annotated image (image with boxes and labels). This image is uploaded to the s3 bucket.
2. From this annotated image, count the number of boxes. Then calculate density by: number of boxes divided by volume of water.
3. Create another function that identifies polymer type given each cropped box in the annotated image in step 1.
4. Count the sum of each labels and identify which labels were present in the image.
5. Using the same sampleID, update attributes in DynamoDB by filling up its density, polymerType, Annotated imageURL.
6. Update front-end to display density and polymerType properly.
