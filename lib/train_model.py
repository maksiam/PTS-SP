import torch
from .models.fcnn_models import InceptModel, CLIPModel
from .models.custom_datasets import CustomDataset
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
import torch.optim as optim
from tqdm import tqdm
import torch.nn as nn


from .utils import evaluate, get_incept_image_embedding, split_and_process_data


device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

model = InceptModel().to(device)

transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),  # Resize images if needed
        transforms.ToTensor(),  # Convert PIL images to tensors
        transforms.Normalize([0.5], [0.5]),
    ]
)

data_dict_train, data_dict_test, data_dict_values_train, data_dict_values_test = (
    split_and_process_data(0.8)
)

train_dataset = CustomDataset(
    data_dict=data_dict_train,
    data_dict_values=data_dict_values_train,
    transform=transform,
    max_combinations=2000,
    split="train",
)
test_dataset = CustomDataset(
    data_dict=data_dict_test,
    data_dict_values=data_dict_values_test,
    transform=transform,
    max_combinations=500,
    split="test",
)
train_loader = DataLoader(train_dataset, batch_size=1)
test_loader = DataLoader(test_dataset, batch_size=1)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Replace the printing of MSE with SMAPE in your training loop
num_epochs = 10  # Adjust number of epochs as needed
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for inputs, labels, targets, _, _ in tqdm(
        train_loader
    ):  # Ignoring empirical mAP and sizes here
        inputs = inputs.to(device)
        labels = labels.to(device)
        targets = targets.to(device)  # Parameters targets
        optimizer.zero_grad()
        outputs = model(
            torch.cat(
                (
                    get_incept_image_embedding(inputs[0]),
                    get_incept_image_embedding(labels[0]),
                ),
                dim=1,
            )
        )
        loss = criterion(outputs, targets.float())
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    # Evaluation
    avg_smape_params = evaluate(model, test_loader, device)
    torch.save(model.state_dict(), "model_incept_v3_fc.pt")
    print(f"Epoch {epoch+1}, Training Loss: {running_loss/len(train_loader)}")
    for i, smape_value in enumerate(avg_smape_params):
        print(f"Validation SMAPE for parameter {i+1}: {smape_value}%")

print("Training finished!")
avg_smape_params = evaluate(model, test_loader, device)
for i, smape_value in enumerate(avg_smape_params, start=1):
    print(f"Test SMAPE for parameter {i}: {smape_value}%")