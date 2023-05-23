import pickle
import matplotlib.pyplot as plt


def visualize_data():
    with open('total_bytes_list.pickle', 'rb') as f:
        total_bytes = pickle.load(f)
    with open('packages_loss_list.pickle', 'rb') as f:
        packages_loss = pickle.load(f)
    with open('packages_loss_rate_list.pickle', 'rb') as f:
        packages_loss_rate = pickle.load(f)
    with open('bits_per_second_list.pickle', 'rb') as f:
        bits_per_second = pickle.load(f)

    plt.subplot(221)
    plt.plot([packages_loss_rate[i][0] for i in range(len(packages_loss_rate))],
             [packages_loss_rate[i][1] * 100 for i in range(len(packages_loss_rate))])
    plt.title("Packages Loss Rate")
    plt.ylabel("rate/%")
    plt.subplot(222)
    plt.plot([packages_loss[i][0] for i in range(len(packages_loss))],
             [packages_loss[i][1] for i in range(len(packages_loss))])
    plt.title("Packages Loss")
    plt.subplot(212)
    plt.plot([total_bytes[i][0] for i in range(len(total_bytes))], [total_bytes[i][1] for i in range(len(total_bytes))])
    plt.plot([bits_per_second[i][0] for i in range(len(bits_per_second))],
             [bits_per_second[i][1] for i in range(len(bits_per_second))])
    plt.xlabel("Time/s")
    plt.title("Video Stream")
    plt.ylabel("bytes")
    plt.legend(["total_bytes", "bits_per_second"])

    # 增加子图之间的垂直间距
    plt.subplots_adjust(hspace=0.5)
    
    plt.tight_layout() # 自动排版

    plt.savefig('result.png')

    # plt.show()


if __name__ == '__main__':
    visualize_data()
    plt.show()
