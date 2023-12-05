import torch
from torchvision import transforms
from torchvision.transforms.functional import to_pil_image
from PIL import Image
from matplotlib import pyplot as plt
import copy
from clipseg.models.clipseg import CLIPDensePredT
from diffusers import StableDiffusionInpaintPipeline, EulerDiscreteScheduler


class ModelClassDep:

    def __init__(self, user_image, user_prompt, user_pattern):
        self.user_image = user_image
        self.user_prompt = user_prompt
        self.user_pattern = user_pattern

    def model_execution(self):
        model = CLIPDensePredT(version='ViT-B/16', reduce_dim=64)
        model.load_state_dict(torch.load('clipseg/weights/rd64-uni.pth', map_location=torch.device('cuda')), strict=False);
        model_dir = "stabilityai/stable-diffusion-2-inpainting"
        # The scheduler determine the algorithm used to produce new samples during the denoising process
        scheduler = EulerDiscreteScheduler.from_pretrained(model_dir, subfolder="scheduler")
        pipe = StableDiffusionInpaintPipeline.from_pretrained(model_dir, scheduler=scheduler, variant="fp16",
                                                              torch_dtype=torch.float16)
        pipe = pipe.to("cuda")
        pipe.enable_xformers_memory_efficient_attention()
        # Example image from unsplash.com
        target_width, target_height = 512, 512
        source_image = Image.open(self.user_image)
        width, height = source_image.size
        print(f"Source image size: {source_image.size}")
        source_image = source_image.crop((0, height - width, width, height))
        source_image = source_image.resize((target_width, target_height), Image.LANCZOS)
        print(f"Target image size: {source_image.size}")
        # Setup transformations to be applied to the image
        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]), ])
        tensor_image = transform(source_image).unsqueeze(0)

        # Create masks for the parts of the clothes to be identified
        prompts = self.user_prompt
        # Use ClipSeg to identify elements in picture
        with torch.no_grad():
            preds = model(tensor_image.repeat(len(prompts), 1, 1, 1), prompts)[0]

        def create_image_grid(original_image, images, names, rows, columns):
            names = copy.copy(names)
            images = copy.copy(images)
            if torch.is_tensor(images):
                assert images.size(0) == len(names), "Number of images and names should be equal"
                assert images.size(0) >= (rows * columns) - 1 - 1, "Not enough images for the specified grid size"
                images = [to_pil_image(torch.sigmoid(img)) for img in images]
            else:
                assert len(images) == len(names), "Number of images and names should be equal"
            assert len(images) >= (rows * columns) - 1 - 1, "Not enough images for the specified grid size"
            names.insert(0, '')
            fig, axes = plt.subplots(rows, columns, figsize=(15, 15))
            for idx, (img, name) in enumerate(zip(images, names)):
                row, col = divmod(idx, columns)
                axes[row, col].imshow(img, cmap='gray' if idx > 0 and torch.is_tensor(images) else None)
                axes[row, col].set_title(name)
                axes[row, col].axis('off')
            for idx in range(len(images), rows * columns):
                row, col = divmod(idx, columns)
                axes[row, col].axis('off')
            plt.tight_layout()
            plt.show()

        create_image_grid(self.user_image, preds, prompts, 2, 3)

        # Decide which mask you want to do inpainting with. In this case we pick the skirt which is mask number 1
        mask_number = 2
        processed_mask = torch.special.ndtr(preds[mask_number][0])
        stable_diffusion_mask = transforms.ToPILImage()(processed_mask)
        # Setup transformation prompts
        num_images_per_prompt = 4
        inpainting_prompts = self.user_pattern
        generator = torch.Generator(device="cuda").manual_seed(101)  # 155, 77,

        # Run Stable Difussion pipeline in inpainting mode
        encoded_images = []
        for i in range(num_images_per_prompt):
            image = pipe(prompt=inpainting_prompts[i], guidance_scale=7.5, num_inference_steps=60, generator=generator,
                         image=source_image, mask_image=stable_diffusion_mask).images[0]
            encoded_images.append(image)

        return create_image_grid(source_image, encoded_images, inpainting_prompts, 2, 3)


if __name__ == '__main__':
    x = ModelClassDep(r"C:\Users\razor\Downloads\Kevin_De_Bruyne.jpg",['red boots','red shorts','red shirt', 'tattoo on arm'],["black lines","red blue green","flowers","japanese kimono"])
    x.model_execution()
