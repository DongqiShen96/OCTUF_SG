import argparse
import os
import warnings
# from model import *
from model_octuf import *
import torch.optim as optim
from data_processor import *
from trainer_octuf import *
from scheduler import *
import numbers
from config import *
import matplotlib.pyplot as plt
import torchvision


warnings.filterwarnings("ignore")


def main():
    global args
    args = parser.parse_args()
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # Create save directory
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
        
    model_dir = "./%s/%s_layer_%d_lr_%.4f_ratio_%.2f" % (args.save_dir, args.model, args.layer_num, args.lr, args.sensing_rate)
    log_file_name = "%s/%s_layer_%d_lr_%.4f_ratio_%d.txt" % (model_dir, args.model, args.layer_num, args.lr, args.sensing_rate)
    if not os.path.exists(model_dir):
        print("model_dir:", model_dir)
        os.mkdir(model_dir)
    torch.backends.cudnn.benchmark = True

    model = OCTUF(LayerNo=args.layer_num, sensing_rate=args.sensing_rate)
    model = nn.DataParallel(model)
    model = model.to(device)
    
    num_count = 0
    num_params = 0
    for para in model.parameters():
        num_count += 1
        num_params += para.numel()
#         print('Layer %d' % num_count)
#         print(para.size())
    print("total para num: %d" % num_params)

    criterion = F.mse_loss
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    scheduler_cosine = optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epochs - args.warm_epochs, eta_min=args.last_lr)
    scheduler = GradualWarmupScheduler(optimizer, multiplier=1, total_epoch=args.warm_epochs,
                                       after_scheduler=scheduler_cosine)

    train_loader = data_loader(args)
    print("train_loader:", train_loader, len(train_loader))

    if args.start_epoch > 0:
        pre_model_dir = model_dir
        checkpoint = torch.load("%s/net_params_%d.pth" % (pre_model_dir, args.start_epoch))
        model.load_state_dict(checkpoint['net'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        start_epoch = checkpoint["epoch"] + 1
        for i in range(0, start_epoch):
            scheduler.step()
    else:
        start_epoch = args.start_epoch + 1
        scheduler.step()

    print("Model: %s , Sensing Rate: %.2f , Epoch: %d , Initial LR: %f\n" % (
        args.model, args.sensing_rate, args.epochs, args.lr))

    print('Start training')
    for epoch in range(start_epoch, args.epochs + 1):
        print('current lr {:.5e}'.format(scheduler.get_lr()[0]))
        loss = train(train_loader, model, criterion, args.sensing_rate, optimizer, device)
        print("******************")
        scheduler.step()
        print_data = "[%02d/%02d]Total Loss: %f, learning_rate: %.5f\n" % (epoch, args.epochs, loss, scheduler.get_lr()[0])
        print(print_data)
        output_file = open(log_file_name, 'a')
        output_file.write(print_data)
        output_file.close()

        if epoch % 5 == 0:
            checkpoint = {
                'epoch': epoch,
                'net': model.state_dict(),
                'optimizer': optimizer.state_dict(),
            }
            print("model_dir:", model_dir)
            torch.save(checkpoint, "%s/net_params_%d.pth" % (model_dir, epoch))

    print('Trained finished.')

    print('Train sg')
#========================================================================================
    def save_image(tensor, filename):
        grid = torchvision.utils.make_grid(tensor)  
        npgrid = grid.cpu().numpy()  
        plt.figure(figsize=(10, 10))
        plt.imshow(np.transpose(npgrid, (1, 2, 0)))
        plt.axis('off')
        plt.savefig(filename)
        plt.close()

    # def save_image(tensor, filename):
    #     # Only take the first three channels.
    #     tensor = tensor[:, :3, :, :]
    #     grid = torchvision.utils.make_grid(tensor)  
    #     npgrid = grid.cpu().numpy()  
    #     plt.figure(figsize=(10, 10))
    #     plt.imshow(np.transpose(npgrid, (1, 2, 0)))
    #     plt.axis('off')
    #     plt.savefig(filename)
    #     plt.close()

    avg_loss = 0
    count = 0
    checkpoint_path = "%s/net_params_%d.pth" % (model_dir, 84)  # specify the correct epoch

    if os.path.isfile(checkpoint_path):
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint['net'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        start_epoch = checkpoint['epoch'] + 1
        print("Loaded checkpoint from '{}'".format(checkpoint_path))
    else:
        print("No checkpoint found at '{}'".format(checkpoint_path))
        start_epoch = 0

    # Resume training from the loaded checkpoint or from scratch if no checkpoint was found
    for epoch in range(start_epoch, 86):
        avg_epoch_loss = 0  # Variable to store the average loss for each epoch
        avg_loss = 0
        for data in train_loader:
            data = data.to(device)
            optimizer.zero_grad()
            outputs = model(data)
            loss = criterion(outputs, data)
            avg_loss += loss.cpu().data.numpy()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()
            count += 1
            if count % 1000 == 0:
                print(epoch, count, loss)

        detached_outputs = outputs.detach()
        save_image(detached_outputs, f'image_at_epoch_{epoch+1}.png')

        # Calculate the average loss for the epoch
        avg_epoch_loss = avg_loss / len(train_loader)
        print('Epoch {} Average Loss: {}'.format(epoch, avg_epoch_loss * 100))


        if epoch % 1 == 0:
            checkpoint = {
                'epoch': epoch,
                'net': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict(),
            }
            print("model_dir:", model_dir)
            torch.save(checkpoint, "%s/OCTUF_SG_net_params_%d.pth" % (model_dir, epoch))
    # for epoch in range(epoch_num):
    #     for data in train_loader:
    #         #bs = data.size()[0]
    #         data = data.to(device)
    #         optimizer.zero_grad()
    #         outputs = model(data)
    #         loss = criterion(outputs, data) 
    #         avg_loss += loss.cpu().data.numpy()
    #         loss.backward()
    #         torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
    #         optimizer.step()
    #         count += 1
    #         if count % 100 == 0:
    #             print('Epoch-{}; Count-{}; loss: {};'.format(epoch, count, avg_loss))
    #             if count % 1000 == 0:
    #                 torch.save(model.state_dict(),'save/weights_%d.tar'%(count))
    #             avg_loss = 0
    #     detached_outputs = outputs.detach()
    #     save_image(detached_outputs, f'image_at_epoch_{epoch+1}.png')

    # if epoch % 5 == 0:
    #         checkpoint = {
    #             'epoch': epoch,
    #             'net': model.state_dict(),
    #             'optimizer': optimizer.state_dict(),
    #         }
    #         print("model_dir:", model_dir)
    #         torch.save(checkpoint, "%s/OCTUF_SG_net_params_%d.pth" % (model_dir, epoch))



    
    # print('Signalling game Train start.')
    # #optimizer = optim.Adam(model.parameters(), lr=learning_rate, betas=(beta1,0.999))
   
    # avg_loss = 0
    # count = 0
    # for epoch in range(epoch_num):
    #     for data in train_loader:
    #         bs = data.size()[0]
    #         data = data.to(device)
    #         optimizer.zero_grad()
    #         outputs = model(data)  # Pass data through the model
    #         loss = criterion(outputs, data.to(device))  # Also move target data to device
    #         avg_loss += loss.item()
    #         loss.backward()
    #         torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
    #         optimizer.step()
    #         count += 1
    #         if count % 100 == 0:
    #             print('Epoch-{}; Count-{}; loss: {};'.format(epoch, count, avg_loss / 100))
    #             if count % 1000 == 0:
    #                 torch.save(model.state_dict(), 'save/weights_%d.tar' % (count))
    #             avg_loss = 0
    # torch.save(model.state_dict(), 'save/weights_final.tar')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='OCTUF', help='model name')
    parser.add_argument('--sensing_rate', type=float, default=0.100000, help='set sensing rate')
    parser.add_argument('--start_epoch', default=80, type=int, help='epoch number of start training')
    parser.add_argument('--warm_epochs', default=3, type=int, help='number of epochs to warm up')
    parser.add_argument('--epochs', default=80, type=int, help='number of total epochs to run')
    parser.add_argument('-b', '--batch_size', default=16, type=int, help='mini-batch size')
    parser.add_argument('--block_size', default=32, type=int, help='block size')
    parser.add_argument('--lr', '--learning_rate', default=5e-4, type=float, help='initial learning rate')
    parser.add_argument('--last_lr', default=5e-5, type=float, help='initial learning rate')
    parser.add_argument('--save_dir', help='The directory used to save the trained models',
                        default='save_OCTUF', type=str)
    parser.add_argument('--layer_num', type=int, default=10, help='phase number of the Net')
    main()
