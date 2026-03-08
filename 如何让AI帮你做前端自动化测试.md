# 如何让AI帮你做前端自动化测试？我们这样落地了

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/Z6bicxIx5naKOan4r2LKicULAkOcuENs7LATS1icdNuTjD2JSXyqQ7RunPMRVyZ1ZsbWVkC0QyMuWEn7voejicge1w/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)



阿里妹导读





本文介绍了一个基于AI的UI自动化测试框架在专有云质量保障中的工程化实践。

##  

引言

随着AI大模型技术的快速发展并在各行业/场景下的爆发式应用，如何利用AI技术提高测试效率也成为了热门话题。具体到我们团队的日常工作中，一个痛点就是前端测试很耗费人力，体现在：

1. 前端用例自动化率低/无自动化，每个版本、每轮测试依赖手工执行，在多版本、快速迭代的背景下就会导致覆盖不足，漏到客户现场的前端缺陷多
2. 前端自动化实现门槛高、且维护成本大，在版本快速迭代的背景下，前端页面更新换代很快，会出现一个版本花大力气实现的自动化用例，在下个版本因为前端元素变动导致无法执行，还需要继续投入大量人力进行适配的情况

借助AI的能力，让解决这一痛点成为了可能，也即本文将要介绍的“基于AI的UI自动化测试框架”在专有云质量保障的工程化落地。

------

核心原理



**技术栈**

框架主要使用了开源的browser-use[1]工具，此外主要使用了如下技术栈：

- playwright[2]：用于前端操作、元素判断，browser-use也是使用它实现的
- pytest[3]：用例管理和调度
- allure[4]：测试报告生成
- 大模型选用的是qwen-max



**架构**

框架图

![图片](https://mmbiz.qpic.cn/mmbiz_png/Z6bicxIx5naKOan4r2LKicULAkOcuENs7Lb4UWkY00JN8v4icJFLPb6ofcibGx1mTw44HXMqlFaxiaoIywyLtib0eH0g/640?wx_fmt=png&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=1)

主要包括：

- 后端服务层，用于提供服务给外部调用或集成，如web server、cicd
- 框架管理层，主要完成用例的管理和调度
- 测试用例层，主要为用例自动化需要用到的各个模块

流程图

![图片](https://mmbiz.qpic.cn/mmbiz_png/Z6bicxIx5naKOan4r2LKicULAkOcuENs7L5QVCoWFccO1uibiaPldXdUScvzxdaPvqT58pCiawt3ZEGcLEEZBTjZz5A/640?wx_fmt=png&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=2)

主要分为三个部分：

1. 测试任务的管理、调度、结果展示部分，即左上部分；
2. 测试用例的编写、维护、管理部分，即右上部分；
3. 测试执行的运行时管理部分，即下半部分；



**实现机制**

#### 1. 自然语言驱动的测试用例

测试用例的编写采用yaml格式，将测试步骤以自然语言的方式编写为用例，框架会读取并分步以prompt提示词的形式与大模型交互，转换为具体的action调用。 下面是一个简单的VPC创建用例：

```
testType: ascmtestName: create_vpc_uniquetestId: 74****98, 74****3testDescription: 使用默认参数创建VPCpreSteps:  - common/product/ascm/login.yamltestSteps:  - task: 打开"{{ ASCM_URL }}/vpc/console/vpcPage?{{ DEFAULT_ORG_ID }}"  - task: 点击“创建专有网络”按钮    # {{ VPC_NAME_UNIQUE }} 为用例自定义变量，参见py文件  - task: 在“专有网络名称”输入框输入“{{ VPC_NAME_UNIQUE }}”  - task: 点击“提交”按钮
```

``

其中的重点在preSteps和testSteps：

- preSteps也即用例的前置步骤，并不是当前测试所关心的内容，因此可以引用common/product下的公共文件，比如示例中就是ascm登录操作；引用的文件也是以yaml形式组织的原子类/公共类步骤，实际执行为重放的方式（见后文），框架会递归解析并判断是否有循环引用
- testSteps为当前测试需要执行的步骤，也即大模型能直接看到的提示词，因此用例的编写实质上转换为提示词工程(PE)，如何让大模型准确的理解需求并完成操作，是实现用例自动化的要考虑的核心问题 另外task中的“{{ }}”为Jinja2格式的变量，框架会根据用例的实际执行环境，替换为对应的值，支持全局层面已定义好的变量、用例自定义使用到的变量

关于提示词的组织原则，以及具体的实现原理，内容较多，后续会单独写一篇进行分析。

#### 2. 动态元素定位

在传统的UI自动化实现中，一般会根据页面的xpath、css selector等方式，定位到具体元素然后进行后续操作。这也是维护成本高的一个主要原因，因为一旦页面排布发生变化，用例就无法执行。 browser-use在这里有较大的优势，它的稳定性好，是决定我们技术选型的一个重要因素。具体机制为：

- browser-use会抓取当前页面存在的元素，并以文本方式组织成大模型能理解的内容，同时若大模型具备视觉能力，也会将当前截图一并提供，便于大模型识别和决策出用户需要操作的元素是什么。因此只要提示词足够准确，在页面内容没有翻天覆地变化的情况下，均可以动态定位到具体元素
- 在大模型决策出使用的action和操作的元素后，这部分元素信息会被保存下来用于后续回放执行时的辅助定位。主要包括元素的xpath、attributes和完整的parent层级，在回放执行中，若当前页面元素的index编号与前述执行不一致，会根据保存的信息进行页面遍历搜索，然后更新为新找到的index编号来操作

#### 3. 执行回放与自适应更新

使用AI的过程中有两个问题是必须要考虑的：

1. token使用量，在大量的测试用例自动化之后，多个环境、多个版本执行，会发起大量的大模型交互、消耗大量token
2. 大模型进行分析决策的速度问题，也即速度、效果、价格不能兼得，同时过程中会伴随着较多网络交互，也会影响用例的执行速度

基于这两个问题，框架支持了测试回放能力，即大模型决策生成的action调用和参数保存为json文件，在测试调度执行的时候，优先会执行json文件中内容的回放，这里完全不涉及大模型调用，并且用到了2中提到的index更新能力；若回放失败，再调用大模型执行，同时更新json文件为新生成的内容。

#### 4. 断言机制

browser-use的设计目的是利用AI能力，分析用户给出的task并规划出相应操作浏览器的行为直至完成task。显然它是以目标为导向，自动化完成任务的一个工具，并不是天然为自动化测试设计的工具，所以它缺少测试需要的最关键一环，也就是断言。 测试框架补充了这一部分，在对应的task执行后，能够对当前浏览器页面进行元素抓取和结果判断。 框架设计上支持3种断言能力，当前已实现2种，1种实现中：

1. playwright原生断言能力，同样以前述创建VPC用例为例，最后一个task里可以这么写：

```
  - task: 点击“提交”按钮    expected:      - type: playwright        locator: get_by_text("操作成功", exact=True)        method: to_be_visible()
```

此处type告诉框架为playwright断言、locator为playwright的page locator支持的所有方法[5]、method为locator支持的所有expect assertion方法[6]这种方式的优点是即开即用，断言严格且准确，适合需要精确判断的用例场景

2. 用例自定义断言能力，type值改为validator，由测试用例自己实现validator函数并解析后续的yaml expected字段，以进行用例定制化的判断
3. 大模型断言（实现中），type值改为ai，调用大模型能力，对自然语言进行解析，结合当前页面元素、截图进行判断，可能存在不稳定性

------

实施过程中的挑战与解决方案

在框架的开发、用例实现和调试过程中，遇到了比较多的问题，这里挑几类典型问题及其应对方案进行介绍



**1. 大模型幻觉问题**

使用AI能力，就避免不了大模型产生幻觉，这是由大模型的概率特性所决定的。具体来讲，我们遇到了这几个问题：

- **对action产生幻觉**

虽然系统提示词中写明了"Don't hallucinate actions"，大模型不会返回不存在的action，但在规划出具体应该使用什么action以及当前状态上，会出现和步骤task目的不匹配的情况。特别是在页面出现异常的场景下（如未完全加载成功），大模型会尝试使用scroll_down、go_back等多种action来操作，导致最终任务失败。解决方案采用了如下两种：

- - **task拆分**，在测试用例编写规范中，我们指明了很多规则，其中几条可以改善这个情况，如：task本身完成的任务要尽可能简单和明确、如果task过于复杂则需要拆分为多步、如果上一个操作执行后页面元素会变化，则需要将后续操作拆分到下一个task中，以强制大模型更新当前状态
  - **大模型最大步骤限制**，browser-use默认的设置是100，它的设计是希望大模型能从用户给出的任何目标中规划出具体步骤并以迭代的方式执行直至最终达成目标。这显然不适用于测试步骤，而且从用例编写上，我们不希望每一步太复杂，因此规划出的action不应该太多，经过调试，这个数字我们限制在了3，即一旦一个测试步骤没有在3个action以内达成，则认为此步骤失败

- **对task目标产生幻觉**

  在某些测试步骤task已经完成后，会出现大模型继续决策产生幻觉action调用的情况，进而导致非预期的状态，影响后续task。这个问题与task本身的内容关系较大，但无法归纳出哪些情况下会出现。 好在框架本身设计上就是使用的browser-use的follow up task能力，将测试用例分步骤提供给大模型的，因此在每个task提示词之后，框架默认加上了“... and done”，引导大模型在决策出对应的action后，再加上“done” action。由于系统提示词中指明了“Use the done action as the last action as soon as the ultimate task is complete”，结合起来就能较稳定的避免task幻觉问题，下面是一个常见的task规划结果：

```
"action": [    {      "click_element_by_index": {        "index": 264      }    },    {      "wait": {        "seconds": 1      }    },    {      "done": {        "text": "Clicked on the 'VPC ID:vpc-ad7*******j9ap' link and waited for 1 second, task completed.",        "success": true      }    }  ]
```

- **对断言产生幻觉**

框架中的断言模块利用了browser-use的custom action能力，即扩展了大模型可以使用的function_calling tools。大模型看到task中需要进行断言时，会决策调用框架的expected action处理。实际使用中会出现两种非预期情况：大模型返回的决策结果中实际没有调用、断言失败后大模型误认为task没有完成而继续执行其它操作。

解决这两种情况依然是要从提示词入手，browser-use支持对系统提示词进行修改，即Override和Extend两种方式。框架采用的当然是Extend，browser-use的系统提示词是经过大量测试的，Override可能会导致很多稳定性问题。在系统提示词中，我们增加了如下章节：

```
REMEMBER the most important RULE:1. ALWAYS use 'expected' tool with the provided expected string in the task2. If 'expected' action is not success, just stop the task and done with the message 
```

``



**2. browser-use与测试场景的适配**

前文也有提到，browser-use的设计目的和我们工程化要应用的测试场景，还是有一些偏差的，在使用的过程中主要遇到两种问题：

- **browser-use本身的缺陷和不足**

我们遇到了诸如设置keepalive为True之后browser资源无法销毁、点击元素跳转到新tab后元素抓取仍然在原tab中进行等缺陷。有些缺陷在新版本的browser-use中修复了，有些还没有。 依赖browser-use本身的版本迭代无法满足我们的需求，因此框架层面直接将browser-use的核心对象派生后进行定制化修改。一方面可以快速修复发现的问题，这里的修复可能是直接解决问题、也可能是通过适配绕开问题；另一方面可以在已有功能的基础上，开发我们需要的功能，如agent run方法的前后置hook接口，在history rerun时不支持，我们进行了补充，进而实现了每个测试步骤之后都能自动截图等功能，且大模型调用和回放执行效果一致。 这种方式避免了直接修改browser-use源码，因此后续升级browser-use版本不会存在冲突问题，同时又能享受开源社区贡献的成果。

- **测试场景需要的能力缺失**

我们的主要目的是实现UI自动化测试，browser-use并不能完成所有事情，因此在框架层面，对缺失的能力进行了补充实现，并完成了与browser-use功能的结合，主要为：

- - 断言能力，前述章节已经介绍了相关机制，这里不再赘述；
  - 测试调度和执行发起能力，利用了我们团队比较成熟的后端自动化框架经验，使用pytest进行了实现，并接入了现有的IAAS Test测试平台；
  - 测试报告生成和展示，使用allure进行实现，同时结合了基于browser-use定制化的一些能力，下面是一个测试报告示例。

![图片](https://mmbiz.qpic.cn/mmbiz_png/Z6bicxIx5naKOan4r2LKicULAkOcuENs7LJwYBUcrSDrVcuxJK59OTzf1KCWxCIOumdia4c3A15zHKRQyhddYggag/640?wx_fmt=png&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=3)



**3. 页面元素识别问题**

在测试用例自动化的过程中，基本流程是将人眼看到的页面元素，转换成prompt让大模型理解和定位，这里会存在不少gap，出现大模型死活给不出预期元素index信息的情况，我们采取了下面几种方式来改善这个问题：

- **提示词优化**

结合用例调试过程，将与大模型进行交互的信息保存到日志中，辅助优化提示词，其中“[Start of page]”和“[End of page]”之间的内容，即为大模型真实看到的页面元素布局，其中的标签、属性、相对位置等信息能非常好的提升提示词编写的有效性，我们的测试用例编写规范中也针对这一部分进行了说明指导，如“新出现的xx”、“xx后面的yy元素”等。涉及的系统提示词中为如下部分：

```
- Only elements with numeric indexes in [ ] are interactive- (stacked) indentation (with \t) is important and means that the element is a(html) child of the element above(with a lower index)- Elements with \* are new elements that were added after the previous step(if url has not changed)
```

``

- **元素提取范围扩展**


为了控制消耗的token，browser-use并不会抓取所有的页面元素信息传给大模型，如果某些特殊属性能帮助识别唯一元素，可以进行添加，对应如下参数：

```
include_attributes: list[str] = [      'title',      'type',      'name',      'role',      'aria-label',      'placeholder',      'value',      'alt',      'aria-expanded',      'data-date-format',    ],
```

``

- **换个思路&兜底方案**

有些时候并不一定要通过某些难定位元素来完成测试步骤，可以换个思路用一些简单、确定性强的方法组合起来达成目标。 

如果确实无路可走，部分常用action其实支持指定xpath和css selector作为兜底，这种方式就会遇到传统UI自动化的问题，即页面布局变动可能导致定位失效。在一些动态页面的测试中，有过使用：

```
  - task: 鼠标移动到xpath为“//*[@id="icestarkNode"]/main/section[2]/section[2]/section[2]/section/section/div/div/div[1]/div[2]/div/div/div/div[2]/div[2]/table/tbody/tr/td[4]/div/div/div/div”的元素上  - task: 点击新出现的 <i> 元素
```



**4. 测试稳定性**



### 提升自动化用例的执行稳定性，是一个比较大的话题，也是一定需要解决的问题。特别是随着自动化用例数量、测试轮次的增加，无效执行的用例数量会增多，即非产品缺陷导致的用例失败。当前我们采用了下面几个方式：

- **测试用例编写规范**
  task提示词直接决定了大模型决策的稳定性，因此从项目一开始我们就创建了测试用例编写规范文档并持续补充规则，便于不同的人编写用例时进行参考。包括用例通用规则、变量替换使用场景、常用task提示词和action对应关系、常见问题及修改方案等。 基于此规范，提示词的准确性能够得到提升，结合框架的自适应更新机制，能够实现有效的测试稳定性提升。

- **模型稳定性**
  也即模型调优，初期主要依靠qwen系列的模型选型、参数调整（top_p/temperature/seed）来提升稳定性。后续会使用模型训练和微调来让大模型更懂我们的应用场景

- **环境健康检查及feature检测**
  在测试执行前会对环境的健康状态及具备的feature进行检查，以此决定调度的用例是否能执行。一个具体的例子就是ascm服务目录功能，集群部署与否、开关打开与否，均会全局性的影响实例创建页面的元素布局和文本展示。我们主要采取了如下3种方案：

- - 如果页面会被类似功能影响，则task提示词中需要指明不同情况下的操作方式；
  - 如果过于复杂无法在提示词中兼容，则可以将用例拆分为不同场景编写，结合框架的feature检测和pytest的@pytest.mark.skipif实现不同场景执行不同用例；
  - 框架在环境检查阶段，将全局性开关恢复为默认状态再进行用例调度；针对开关及对应功能本身的测试，则由相关用例负责配置和处理；

- **使用大模型但不依赖大模型**
  对于某个具体的前端测试用例，只关心自己的步骤操作及结果，对于前置步骤、依赖等，没有必要依然靠大模型解析页面并一步步操作完成，可以直接使用更快速、稳定的后端API能力。因此框架支持了云产品的后端API调用，包括OpenAPI、InnerAPI和OpsAPI，测试用例可以在setup阶段直接调用完成前置步骤/资源创建和配置。

**参考链接：**

[1] https://github.com/browser-use/browser-use

[2] https://playwright.dev/python/

[3] https://docs.pytest.org/en/stable/

[4] https://allurereport.org/

[5] https://playwright.dev/python/docs/api/class-locator#methods

[6] https://playwright.dev/python/docs/api/class-locatorassertions#methods
